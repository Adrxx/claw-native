"""Bounded local milestone checks; passing prefixes never imply playable acceptance."""
import argparse
import datetime
import fcntl
import hashlib
import gzip
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import time
import uuid

from .paths import ROOT, ORIGINAL_SHA256

SCHEMA = 1
CHECKS = ('project', 'source_graph', 'tls_manager_source', 'tls_values_source', 'cold_module_source', 'application_thread_source', 'application_object_source', 'crt_registry_source', 'static_startup_prefix', 'static_startup_three', 'static_startup_seven', 'static_startup_fifteen', 'static_startup_thirtyfour', 'static_startup_application', 'static_startup_extended', 'static_startup_list', 'static_startup_final', 'startup_prefix')
SUFFIXES = {'.py', '.swift', '.cpp', '.c', '.h', '.hpp', '.inc', '.txt', '.json', '.sh', '.zsh', '.plist', '.pbxproj', '.xcconfig'}
GOLDENS = ('work/native-mfc-factories-check/reference.json', 'work/native-mfc-thread-records-check/reference.json')
MANAGER_REFERENCE = 'work/native-mfc-tls-manager-source-check/reference.json'
VALUES_REFERENCE = 'work/native-mfc-tls-values-source-check/reference.json'
MODULE_REFERENCE = 'work/native-mfc-cold-module-check/reference.json'
APPLICATION_THREAD_REFERENCE = 'work/native-mfc-application-thread-source-check/reference.json'
APPLICATION_THREAD_REFERENCE_SHA256 = '225e79b28e71fa3934be0c963b18572b2727b84ee6b5b600eb48e3799e06a3fe'
APPLICATION_OBJECT_REFERENCE = 'work/native-mfc-application-object-check/profile-index.json'
APPLICATION_OBJECT_REFERENCE_SHA256 = '0889633df7b2a2befbe91f22119b1c1b7e1b3dddf4c2cf368ccfadd50b37ae82'
STATIC_REFERENCE = 'work/native-static-startup-check/frozen-v1/provenance.json'
STATIC_REFERENCE_SHA256 = '8f53cb3cbc1c6d128a979d76e45fc6c1ead05e015e578a0e73ad241f8275cabb'
STATIC_COUNTS = {
 'two-wrappers-seed0': (1625, 0, 11, 12, 2),
 'two-wrappers-seed1': (1625, 0, 11, 12, 2),
 'registry-allocation-fatal': (1040, 1, 5, 0, 0),
 'second-registration-capacity-stop': (1529, 1, 10, 12, 1),
 'third-constructor-observational-prefix': (1689, 1, 11, 17, 2),
}
STATIC_STATE_IDENTITIES = {'two-wrappers-seed0': '5683a97883bb1512790978b49064be5f0b9f6028706a40557d89afd79f5e72e1', 'two-wrappers-seed1': '5683a97883bb1512790978b49064be5f0b9f6028706a40557d89afd79f5e72e1', 'registry-allocation-fatal': '40f03db8d058b7108b7b92be4161b9aa9f11879011debd86fd18232bd0b184df', 'second-registration-capacity-stop': 'fa4250cb3a3218a34875e983cb06b760f708d8eadbe2d4a56c88414880faa583', 'third-constructor-observational-prefix': 'dc367ee34dac97a74fa6d6a05146a5fd67e5ee287adf2fa17071f8e16d95f785', 'entry-reentry': '3ed899d2b9022d57efe694f6add15e6ecedf5c3550cc68f6235444a75f75b1ed', 'return-reentry': '6619b6e0190854c0efa909b8d28607aa65a739388c1f063b3f612da6fb137295', 'entry-owner': '3ed899d2b9022d57efe694f6add15e6ecedf5c3550cc68f6235444a75f75b1ed', 'return-owner': '6619b6e0190854c0efa909b8d28607aa65a739388c1f063b3f612da6fb137295'}
STATIC_CONTROLS = ('entry-reentry', 'return-reentry', 'entry-owner', 'return-owner')

STATIC_THREE_REFERENCE = 'work/native-static-startup-check/frozen-v2/provenance.json'
STATIC_THREE_REFERENCE_SHA256 = 'ad0f0ff0f7f0a31d0bf4a013dc50b6a2de32c0ce82092a7a28acc170ccc5b570'
STATIC_THREE_COUNTS = {
 'three-wrappers-seed0': (2138, 0, 15, 26, 3),
 'three-wrappers-nested-fs-dirty-receiver': (2144, 0, 15, 26, 3),
 'constructor-section-before-effect-stop': (1880, 1, 12, 24, 2),
 'constructor-section-after-effect-stop': (1882, 1, 12, 24, 2),
 'registry-allocation-fatal': (1041, 1, 5, 0, 0),
 'second-registration-capacity-stop': (1530, 1, 10, 12, 1),
}
STATIC_THREE_STATE_IDENTITIES = {
 'three-wrappers-seed0': '0fe255cf55092f659c8b42bdbb283d9d4ecdbe4f6f71dcd687fa298849f4f92d',
 'three-wrappers-nested-fs-dirty-receiver': '0fe255cf55092f659c8b42bdbb283d9d4ecdbe4f6f71dcd687fa298849f4f92d',
 'constructor-section-before-effect-stop': 'f26a06d71fd5cb86495d35c144beab4984c88c2e09d9a5aa7098357c6ded6844',
 'constructor-section-after-effect-stop': 'f26a06d71fd5cb86495d35c144beab4984c88c2e09d9a5aa7098357c6ded6844',
 'registry-allocation-fatal': '942ed66c179991e6be806b50604a93c634542447da1d297cb7c4401943c67bdb',
 'second-registration-capacity-stop': '84dddbf4d5add70f876e0a5800c96ebd1c3f345279ffea2d4a6dd6938e6b8baf',
 'entry-reentry': '7f5b91cd6848dfe69c2680625e51dc949e327a98245689b4eaa2a34b2716159f',
 'return-reentry': '62d671bd65164240063c1cd6c127b1882f0145faef0c30928300acd6e64ec479',
 'entry-owner': '7f5b91cd6848dfe69c2680625e51dc949e327a98245689b4eaa2a34b2716159f',
 'return-owner': '62d671bd65164240063c1cd6c127b1882f0145faef0c30928300acd6e64ec479',
}
STATIC_SEVEN_CONTROLS = STATIC_CONTROLS + ('entry-table', 'return-table')
STATIC_TABLE_MUTATION = {'address': 0x522018, 'before': 0x503722, 'after': 0x503748}
STATIC_SEVEN_REFERENCE = 'work/native-static-startup-check/frozen-v3/provenance.json'
STATIC_SEVEN_REFERENCE_SHA256 = 'c7bc36d3161026825f768d349e55616962b632158b6626fdb61c20ebf8332a15'
STATIC_SEVEN_COUNTS = {'seven-wrappers-seed0': (3274, 0, 27, 50, 7),
 'seven-wrappers-nested-fs-dirty-receiver': (3280, 0, 27, 50, 7),
 'constructor-section-before-effect-stop': (1880, 1, 12, 24, 2),
 'constructor-section-after-effect-stop': (1882, 1, 12, 24, 2),
 'registry-allocation-fatal': (1041, 1, 5, 0, 0),
 'second-registration-capacity-stop': (1530, 1, 10, 12, 1),
 'eighth-constructor-observational-prefix': (3346, 1, 27, 55, 7)}
STATIC_SEVEN_STATE_IDENTITIES = {'seven-wrappers-seed0': '6f62ff98f5cfbbed80e8fe727b15e650a6c0ebb5be191a2b65edc19e84ccf70a',
 'seven-wrappers-nested-fs-dirty-receiver': '6f62ff98f5cfbbed80e8fe727b15e650a6c0ebb5be191a2b65edc19e84ccf70a',
 'constructor-section-before-effect-stop': 'f26a06d71fd5cb86495d35c144beab4984c88c2e09d9a5aa7098357c6ded6844',
 'constructor-section-after-effect-stop': 'f26a06d71fd5cb86495d35c144beab4984c88c2e09d9a5aa7098357c6ded6844',
 'registry-allocation-fatal': '942ed66c179991e6be806b50604a93c634542447da1d297cb7c4401943c67bdb',
 'second-registration-capacity-stop': '84dddbf4d5add70f876e0a5800c96ebd1c3f345279ffea2d4a6dd6938e6b8baf',
 'eighth-constructor-observational-prefix': 'c0731b466772e220855414bc4e94b233fe9c78be4fed86819f0d990fc4e83d33',
 'entry-reentry': '7f5b91cd6848dfe69c2680625e51dc949e327a98245689b4eaa2a34b2716159f',
 'return-reentry': '62d671bd65164240063c1cd6c127b1882f0145faef0c30928300acd6e64ec479',
 'entry-owner': '7f5b91cd6848dfe69c2680625e51dc949e327a98245689b4eaa2a34b2716159f',
 'return-owner': '62d671bd65164240063c1cd6c127b1882f0145faef0c30928300acd6e64ec479',
 'entry-table': 'df8aa85938b64f389de7640558ed7953cf9c0c1aa050c39377b5176bda9aee44',
 'return-table': 'b281e10dba12740b7617c80f9918f142de2c2b0ca65a4a0d992a1c8e51af88d3'}
STATIC_FIFTEEN_REFERENCE = 'work/native-static-startup-check/frozen-v4/provenance.json'
STATIC_FIFTEEN_REFERENCE_SHA256 = '5735038a9cffa1ec467d7b379722f2b1bef85c972b8369300606d70d9fd4e86d'
STATIC_FIFTEEN_COUNTS = {'fifteen-wrappers-seed0': (7296, 0, 59, 114, 15),
 'fifteen-wrappers-nested-fs-dirty-receiver': (7304, 0, 59, 114, 15),
 'constructor-section-before-effect-stop': (1930, 1, 12, 24, 2),
 'constructor-section-after-effect-stop': (1932, 1, 12, 24, 2),
 'registry-allocation-fatal': (1053, 1, 5, 0, 0),
 'second-registration-capacity-stop': (1563, 1, 10, 12, 1),
 'sixteenth-constructor-observational-prefix': (7397, 1, 59, 119, 15),
 'range-allocation-before-effect-stop': (3527, 1, 28, 56, 7),
 'range-allocation-after-effect-stop': (3531, 1, 28, 56, 7),
 'range-allocation-failure-observational-prefix': (3549, 1, 28, 57, 7)}
STATIC_FIFTEEN_CONTROL_COUNTS = {'entry-reentry': (1404, 1, 5, 3, 0),
 'return-reentry': (1425, 1, 5, 4, 0),
 'entry-owner': (1404, 1, 5, 3, 0),
 'return-owner': (1425, 1, 5, 4, 0),
 'entry-table': (3073, 1, 21, 41, 5),
 'return-table': (3094, 1, 21, 42, 5)}
STATIC_FIFTEEN_STATE_IDENTITIES = {'fifteen-wrappers-seed0': '6dae1eb42315b479128042ac4937084c41172e9022cc34e61f84245ffa74f3f1',
 'fifteen-wrappers-nested-fs-dirty-receiver': '6dae1eb42315b479128042ac4937084c41172e9022cc34e61f84245ffa74f3f1',
 'constructor-section-before-effect-stop': 'f26a06d71fd5cb86495d35c144beab4984c88c2e09d9a5aa7098357c6ded6844',
 'constructor-section-after-effect-stop': 'f26a06d71fd5cb86495d35c144beab4984c88c2e09d9a5aa7098357c6ded6844',
 'registry-allocation-fatal': '942ed66c179991e6be806b50604a93c634542447da1d297cb7c4401943c67bdb',
 'second-registration-capacity-stop': '84dddbf4d5add70f876e0a5800c96ebd1c3f345279ffea2d4a6dd6938e6b8baf',
 'sixteenth-constructor-observational-prefix': '2237c0cd3c5dfca9540b84f7f40aaf0fc1975359fae01127a206d50c120eec26',
 'range-allocation-before-effect-stop': '1f7347a154fc1c7d0d3524a332304bf4d8c6535d7095bf3b8a08cb7e3fdaf1ad',
 'range-allocation-after-effect-stop': '1f7347a154fc1c7d0d3524a332304bf4d8c6535d7095bf3b8a08cb7e3fdaf1ad',
 'range-allocation-failure-observational-prefix': '327e8d3b898cbea8304da7374c03943e2b8be10833f20e10d2a7f4e112fb622b',
 'entry-reentry': '7f5b91cd6848dfe69c2680625e51dc949e327a98245689b4eaa2a34b2716159f',
 'return-reentry': '62d671bd65164240063c1cd6c127b1882f0145faef0c30928300acd6e64ec479',
 'entry-owner': '7f5b91cd6848dfe69c2680625e51dc949e327a98245689b4eaa2a34b2716159f',
 'return-owner': '62d671bd65164240063c1cd6c127b1882f0145faef0c30928300acd6e64ec479',
 'entry-table': 'df8aa85938b64f389de7640558ed7953cf9c0c1aa050c39377b5176bda9aee44',
 'return-table': 'b281e10dba12740b7617c80f9918f142de2c2b0ca65a4a0d992a1c8e51af88d3'}
STATIC_FIFTEEN_SCOPE_IDENTITIES = {'fifteen-wrappers-seed0': '088cbaaa250704346fdeca417f622bf8ebb500ddc5b17822663c7eeccbebc5a0',
 'fifteen-wrappers-nested-fs-dirty-receiver': '088cbaaa250704346fdeca417f622bf8ebb500ddc5b17822663c7eeccbebc5a0',
 'constructor-section-before-effect-stop': 'd0a9ef55eb9f643d858e80054310997227e9a3dc73cab2d0ff7fc141488fafd1',
 'constructor-section-after-effect-stop': 'd0a9ef55eb9f643d858e80054310997227e9a3dc73cab2d0ff7fc141488fafd1',
 'registry-allocation-fatal': 'b5496e589d17e8463a065fa1ee90f337572a63b7b57ba676e8e534bed2f10c19',
 'second-registration-capacity-stop': '3cf643c26a0aea980bb96c7a8a327fb5c40287c3710010e5d2d0f5726e3d4582',
 'sixteenth-constructor-observational-prefix': '85fb8626974498fc5c2fa355f705aa525dd00a0b626037a424d6eae0bd984411',
 'range-allocation-before-effect-stop': '11a25597d68921d7dbc0e60fd5f8efe82bf07873ccc47d88c36f7273c5c356a5',
 'range-allocation-after-effect-stop': '11a25597d68921d7dbc0e60fd5f8efe82bf07873ccc47d88c36f7273c5c356a5',
 'range-allocation-failure-observational-prefix': '2fe2612d71989c375e8d19d2d1bfdaac1ca2a447cee5293c75956ac14da8c1bb',
 'entry-reentry': '64d0dd6be7ed9eb296f9d0eb9c117dca1173ed38a33fcb4aac0b16da0d1eedac',
 'return-reentry': 'ed9b33b2862ba8889bd2a3f81227823dd2b5c768caa78b236d214d3c36777602',
 'entry-owner': '64d0dd6be7ed9eb296f9d0eb9c117dca1173ed38a33fcb4aac0b16da0d1eedac',
 'return-owner': 'ed9b33b2862ba8889bd2a3f81227823dd2b5c768caa78b236d214d3c36777602',
 'entry-table': '46e0b22adcaeb3ead720d38e93e100c4c0a80f06beed10bb85ac8e23cdd8c0ad',
 'return-table': 'a126a673a5c5c21033d3d637fad2497c86123ac77846c0d34faeb81563762e37'}
STATIC_THIRTYFOUR_REFERENCE = 'work/native-static-startup-check/frozen-v5/provenance.json'
STATIC_THIRTYFOUR_REFERENCE_SHA256 = '70f08260c2103dfe0791fc6ba30cdf743ae6969129cefdc709da8b9a81bde396'
STATIC_THIRTYFOUR_INTERPRETATION = 'work/native-static-startup-check/frozen-v5/original-row-interpretation.json'
STATIC_THIRTYFOUR_INTERPRETATION_SHA256 = 'b0bb06e5a9c234ae2e4bea3d3e354f41dc5213b6c6a73bd6cfa9e0068f63cbe2'
STATIC_THIRTYFOUR_COUNTS = {'thirtyfour-wrappers-seed0': (20384, 0, 136, 266, 34, 34),
 'thirtyfour-wrappers-nested-fs-dirty-receiver': (20394, 0, 136, 266, 34, 34),
 'constructor-section-before-effect-stop': (1933, 1, 12, 24, 2, 2),
 'constructor-section-after-effect-stop': (1935, 1, 12, 24, 2, 2),
 'registry-allocation-fatal': (1054, 1, 5, 0, 0, 0),
 'second-registration-capacity-stop': (1564, 1, 10, 12, 1, 1),
 'thirtyfifth-constructor-observational-prefix': (20541, 1, 136, 271, 34, 34),
 'range-allocation-before-effect-stop': (3530, 1, 28, 56, 7, 7),
 'range-allocation-after-effect-stop': (3534, 1, 28, 56, 7, 7),
 'range-allocation-failure-observational-prefix': (3552, 1, 28, 57, 7, 7),
 'strlen-before-effect-stop': (7526, 1, 60, 122, 15, 15),
 'strlen-after-effect-stop': (7526, 1, 60, 122, 15, 15),
 'registry-growth-before-effect-stop': (19357, 1, 131, 258, 32, 32),
 'registry-growth-after-effect-stop': (19361, 1, 131, 258, 32, 32),
 'registry-growth-first-realloc-failure': (20565, 0, 138, 266, 34, 33)}
STATIC_THIRTYFOUR_CONTROL_COUNTS = {'entry-reentry': (1879, 1, 5, 3, 0, 0),
 'return-reentry': (1900, 1, 5, 4, 0, 0),
 'entry-owner': (1879, 1, 5, 3, 0, 0),
 'return-owner': (1900, 1, 5, 4, 0, 0),
 'entry-table': (3548, 1, 21, 41, 5, 5),
 'return-table': (3569, 1, 21, 42, 5, 5)}
STATIC_THIRTYFOUR_STATE_IDENTITIES = {'thirtyfour-wrappers-seed0': '857abf5eb6b811acfb75e9bde9cfb125fade059bd941d7db4ff6a65ffce98ed6',
 'thirtyfour-wrappers-nested-fs-dirty-receiver': '857abf5eb6b811acfb75e9bde9cfb125fade059bd941d7db4ff6a65ffce98ed6',
 'constructor-section-before-effect-stop': '5d30007e96e938f1673c6891cabcf10d745f92369f13a266fe1488c61d60be14',
 'constructor-section-after-effect-stop': '5d30007e96e938f1673c6891cabcf10d745f92369f13a266fe1488c61d60be14',
 'registry-allocation-fatal': '79a8f56ba09e3a304b75fe8c8fc1e9c1f2d21f69297db3f67f6a5211b91c2e5f',
 'second-registration-capacity-stop': 'c4ab267f489faced9367ac5be22a2180bfee672b8e26acc698305e4d79e6c3d2',
 'thirtyfifth-constructor-observational-prefix': '1dc5a90ad7a4d403db0fc0e5aa52c9b12584ea31903d5765b30c159d84febc33',
 'range-allocation-before-effect-stop': 'a3800847ad2187de659b12751248cabc5f55b703c39fe6326921e92cc9da3f83',
 'range-allocation-after-effect-stop': 'a3800847ad2187de659b12751248cabc5f55b703c39fe6326921e92cc9da3f83',
 'range-allocation-failure-observational-prefix': 'b70c2ec5a3cdd200e77d72f36d9f47f2775d60a8a28f3be7ed4212c557d0383a',
 'strlen-before-effect-stop': '0be149f836b0295ed085dbfab9794ba6d883e9fb3d7f6fabf876a262500e1059',
 'strlen-after-effect-stop': '0be149f836b0295ed085dbfab9794ba6d883e9fb3d7f6fabf876a262500e1059',
 'registry-growth-before-effect-stop': '59fd59d016a89f9d305f148ce9d36fe019cd601c4fa8233ed6503b9257b60f3e',
 'registry-growth-after-effect-stop': '59fd59d016a89f9d305f148ce9d36fe019cd601c4fa8233ed6503b9257b60f3e',
 'registry-growth-first-realloc-failure': '51778855f3de5b5ae2cd563b14db12b8d565a05ddac58fe4d9f0ec61827d18e1',
 'entry-reentry': '9a703d26c766237d0e0845a6724a5316bb5df12bf7c25e4ae4425bc7c79ecf75',
 'return-reentry': '60b7fbbd9f4dd427a377aa8dc3e8fb0afdcb07c26f9862fd4b41045128839c86',
 'entry-owner': '9a703d26c766237d0e0845a6724a5316bb5df12bf7c25e4ae4425bc7c79ecf75',
 'return-owner': '60b7fbbd9f4dd427a377aa8dc3e8fb0afdcb07c26f9862fd4b41045128839c86',
 'entry-table': '2d7023da5ec1f0e45e99dbf2164399eb626c1a35ec287e8d114ba9aa88db6698',
 'return-table': '7e7e727b950f1c198eed0837a15b365aac6f8de3f3e9b84dc01d0b8d291484a2'}
STATIC_THIRTYFOUR_SCOPE_IDENTITIES = {'thirtyfour-wrappers-seed0': '96a71b2cdca4f04a4aa1f1ed00dcf2f155f0db88bd5e1bf157911ee3c03a2918',
 'thirtyfour-wrappers-nested-fs-dirty-receiver': '96a71b2cdca4f04a4aa1f1ed00dcf2f155f0db88bd5e1bf157911ee3c03a2918',
 'constructor-section-before-effect-stop': '200cfa7249a8de33f978769765538a2887d5b0e9ffe5aa1ebbd71e3e8b329058',
 'constructor-section-after-effect-stop': '200cfa7249a8de33f978769765538a2887d5b0e9ffe5aa1ebbd71e3e8b329058',
 'registry-allocation-fatal': '493130ec0f7a0f47902521ac8ecb12e189f4be023f52bf49141a8963fde7d055',
 'second-registration-capacity-stop': '1fed09e995924154da0cc0ddaf6b07b5d8d6d8a5304aaaa87301c43f38b0ed22',
 'thirtyfifth-constructor-observational-prefix': 'fac504a95c1f08acab0ed2ddd70bdf177e7a2ab2bd4899af9a16cad266f51b3a',
 'range-allocation-before-effect-stop': 'f418ede421ec113e755cdae532cc23c989b7afe235577f6c072891fc77082aac',
 'range-allocation-after-effect-stop': 'f418ede421ec113e755cdae532cc23c989b7afe235577f6c072891fc77082aac',
 'range-allocation-failure-observational-prefix': 'de9d8cd64a288029576e9d15b87f5332c498ad70e99914b5d78407542f5e9c10',
 'strlen-before-effect-stop': 'ec37064b951f721ed2c3f7508d38733bb78b6962fce3e726ff2ce25a2f76b3a9',
 'strlen-after-effect-stop': 'ec37064b951f721ed2c3f7508d38733bb78b6962fce3e726ff2ce25a2f76b3a9',
 'registry-growth-before-effect-stop': '7b74a26778bb7fb5312ff44009dfcd9cf545e2db59d3415e729d68e81b98de77',
 'registry-growth-after-effect-stop': '7b74a26778bb7fb5312ff44009dfcd9cf545e2db59d3415e729d68e81b98de77',
 'registry-growth-first-realloc-failure': 'f192ca741b809e997ddfab66e20ffb65039875c254e3c03951b8ea4c783205be',
 'entry-reentry': 'd6aaf3a88600dd92afe2f6d1d9cc5d0d7762ac2eb17894f23d755fc1750593d7',
 'return-reentry': 'ce160dfcd8dd09211973c0707880dde7fa8d3ca3f5d4281d38d127dc9981a075',
 'entry-owner': 'd6aaf3a88600dd92afe2f6d1d9cc5d0d7762ac2eb17894f23d755fc1750593d7',
 'return-owner': 'ce160dfcd8dd09211973c0707880dde7fa8d3ca3f5d4281d38d127dc9981a075',
 'entry-table': '4b0c8d91517dd49b6751510ddfa8a3caa439746da01498b3dba99eb207b3046e',
 'return-table': 'fc51774ab35dd997c43edfadec468dc2bad0ba0ad01e1774114968547774108b'}
STATIC_APPLICATION_REFERENCE = 'work/native-static-startup-check/frozen-v6/provenance.json'
STATIC_APPLICATION_REFERENCE_SHA256 = 'e78490dd06e1b85dc0ec5fdb9da674472a0da4de2183d70b465baa250385cdc9'
STATIC_APPLICATION_COUNTS = {'joint58-clean': (55857, 0, 260, 520, 58, 57),
 'joint58-nested-fs-dirty': (55867, 0, 260, 520, 58, 57),
 'joint58-cursor-false': (55865, 0, 260, 520, 58, 57),
 'joint59-observational-prefix': (56092, 1, 260, 525, 58, 57),
 'application-cursor-before-effect-stop': (23238, 1, 137, 278, 34, 34),
 'application-cursor-after-effect-stop': (23240, 1, 137, 278, 34, 34),
 'application-strdup-malloc-zero': (55361, 0, 260, 520, 58, 57),
 'module-local-before-effect-stop': (25074, 1, 146, 296, 34, 34),
 'module-local-after-effect-stop': (25078, 1, 146, 296, 34, 34),
 'module-local-allocation-zero': (25242, 1, 147, 298, 34, 34),
 'manager-global-after-effect-stop': (24235, 1, 142, 288, 34, 34),
 'manager-global-allocation-zero': (24724, 1, 146, 290, 34, 34),
 'mfc-tls-index-exhausted': (23959, 1, 140, 288, 34, 34),
 'mfc-tls-publication-false': (56858, 0, 263, 524, 58, 57),
 'post-application-registry-growth-after-effect-stop': (33030, 1, 179, 356, 37, 36)}
STATIC_APPLICATION_CONTROL_COUNTS = {'entry-reentry': (2535, 1, 5, 3, 0, 0),
 'return-reentry': (2560, 1, 5, 4, 0, 0),
 'entry-owner': (2535, 1, 5, 3, 0, 0),
 'return-owner': (2560, 1, 5, 4, 0, 0),
 'entry-table': (4504, 1, 21, 41, 5, 5),
 'return-table': (4529, 1, 21, 42, 5, 5)}
STATIC_APPLICATION_STATE_IDENTITIES = {'joint58-clean': 'd34feef662c50d3254c34b555cc347e199c237c4e7dfe27bb0dad991d2bb50db',
 'joint58-nested-fs-dirty': 'd34feef662c50d3254c34b555cc347e199c237c4e7dfe27bb0dad991d2bb50db',
 'joint58-cursor-false': 'd34feef662c50d3254c34b555cc347e199c237c4e7dfe27bb0dad991d2bb50db',
 'joint59-observational-prefix': '328fa6bfe2d836dc694ff91a80076e857501e5c14be35a087dec646c2ac9320d',
 'application-cursor-before-effect-stop': 'a2fb9511931087062d1c380c8eb8a7252f076b8a0d0bae413083edda4985b385',
 'application-cursor-after-effect-stop': 'a2fb9511931087062d1c380c8eb8a7252f076b8a0d0bae413083edda4985b385',
 'application-strdup-malloc-zero': 'd34feef662c50d3254c34b555cc347e199c237c4e7dfe27bb0dad991d2bb50db',
 'module-local-before-effect-stop': '68569f16618e0456ea99c7951b7e7a7c88ca76a6f3193321e99f0055e36e39a3',
 'module-local-after-effect-stop': '68569f16618e0456ea99c7951b7e7a7c88ca76a6f3193321e99f0055e36e39a3',
 'module-local-allocation-zero': '9278814d817c198a37e4dceef182b39e24776b0037fcf1bf1304b91538072d0b',
 'manager-global-after-effect-stop': '0620c653c70b8761234a170a3ccd2820610f2197550be4f2b8202ecd7483cb56',
 'manager-global-allocation-zero': '0bc8e17129646859ff0e5f52af5e6d684c5aa31fd3ec35889dd4b0cc09828231',
 'mfc-tls-index-exhausted': '68896ceefcb0f731c05ec7d1f86fc7965336688eb6734f0a8a9355965b43105b',
 'mfc-tls-publication-false': 'ce344bf3c8ad59dba307878574369378d491fceb42d95bdae3cc38992f409b9a',
 'post-application-registry-growth-after-effect-stop': '9434cc2505d847211069ba5760e3be9bc92bc0b44f5afb5347c58834b7091913',
 'entry-reentry': 'e50d9aca5fcc4b189038d2d0c3b93138a20eb3cfd8c953d80afccc7e3a241d18',
 'return-reentry': '24370d6094c494c6f02bb63168dd5a776534089b5650c9e60b44a98d137ce8dc',
 'entry-owner': 'e50d9aca5fcc4b189038d2d0c3b93138a20eb3cfd8c953d80afccc7e3a241d18',
 'return-owner': '24370d6094c494c6f02bb63168dd5a776534089b5650c9e60b44a98d137ce8dc',
 'entry-table': '151d2cd93ca0b6c411819efcef2ad003ddb848ab78cbd8ed94a007807c396877',
 'return-table': '689814bdf10b1bcd68bf829b9e900918045ea6e21290bfad48540beee60e8aba'}
STATIC_APPLICATION_SCOPE_IDENTITIES = {'joint58-clean': '36f56a72dea5d2248a06d920a2c1565ee56667fb56a4793b2893f096d056fa9e',
 'joint58-nested-fs-dirty': '36f56a72dea5d2248a06d920a2c1565ee56667fb56a4793b2893f096d056fa9e',
 'joint58-cursor-false': '36f56a72dea5d2248a06d920a2c1565ee56667fb56a4793b2893f096d056fa9e',
 'joint59-observational-prefix': '6e52d6eb2d4cc54db9f04a35fe464bc7a10e1dc97cab4aae9f27977544a22c77',
 'application-cursor-before-effect-stop': '2b95b0d2a054c659c48e4ac2622fc650ff8c122b76142e2eebc7d71cc9961e81',
 'application-cursor-after-effect-stop': '2b95b0d2a054c659c48e4ac2622fc650ff8c122b76142e2eebc7d71cc9961e81',
 'application-strdup-malloc-zero': '36f56a72dea5d2248a06d920a2c1565ee56667fb56a4793b2893f096d056fa9e',
 'module-local-before-effect-stop': 'd0919f5318a4d88d3ffad651158c563b91ea14949dbbd1234d5d26ea2e766931',
 'module-local-after-effect-stop': 'd0919f5318a4d88d3ffad651158c563b91ea14949dbbd1234d5d26ea2e766931',
 'module-local-allocation-zero': '8f5cc2094fe67d6470c1962d5e5a0385945b5417bea91ccfd2b0145f9ec94227',
 'manager-global-after-effect-stop': '009d2e8f44fee754ab43d133a7658968808f17e2cfcd45bd729c15ba48ebf4dc',
 'manager-global-allocation-zero': 'b6b9ba9cc27ab8ce2ff7b95820cb726270f86b4ac721fff58e85694019d6911e',
 'mfc-tls-index-exhausted': 'a34ff2abc67bb104707fb93ed9cc767129b506aa7a3b2204e578bdc1bf62aa87',
 'mfc-tls-publication-false': 'd041276fea8ee1b84240e7397dffa2b267d5cb0d22ba8fb74e072514f272ea1e',
 'post-application-registry-growth-after-effect-stop': '43ebb1ec034a9f6a61d05518b4a4d329ad943e0a577da1383875a1370d7fbdba',
 'entry-reentry': '25af9890d5089b2eac686db111f7cae4fb93e6e16f416aacec98a47ce9ba0dc0',
 'return-reentry': '6b851b9bb4944088354fd0783727d8514696199c428d7775c0edced034ac2465',
 'entry-owner': '25af9890d5089b2eac686db111f7cae4fb93e6e16f416aacec98a47ce9ba0dc0',
 'return-owner': '6b851b9bb4944088354fd0783727d8514696199c428d7775c0edced034ac2465',
 'entry-table': '350e4cf0c007c80c40666b3426fd2fed099de896a6ca4cc5e2a728db37bc582f',
 'return-table': '364cab88d7e282ddfb52315d6ba73327ebc2d2d5081644af91b3d5e61176b803'}
STATIC_APPLICATION_TOTAL_CHECKS = 582943
STATIC_APPLICATION_TOTAL_STATES = 11783

STATIC_EXTENDED_REFERENCE = 'work/native-static-startup-check/frozen-v7/provenance.json'
STATIC_EXTENDED_REFERENCE_SHA256 = 'fd1ec4f31628a1304f451a1a76a4cc726caaa06c59589e5ff452a77daeb6386a'
STATIC_EXTENDED_COUNTS = {'extended119-clean': (166627, 0, 512, 1020, 119, 115),
 'extended119-nested-fs-dirty': (166637, 0, 512, 1020, 119, 115),
 'extended119-cursor-false': (166635, 0, 512, 1020, 119, 115),
 'extended120-observational-prefix': (167052, 1, 512, 1025, 119, 115),
 'string-range-malloc-before-effect-stop': (57577, 1, 264, 538, 59, 58),
 'string-range-malloc-after-effect-stop': (57581, 1, 264, 538, 59, 58),
 'string-range-malloc-zero-original-mode4': (164280, 0, 512, 1002, 119, 115),
 'post58-registry-growth-before-effect-stop': (62786, 1, 276, 578, 61, 60),
 'post58-registry-growth-after-effect-stop': (62790, 1, 276, 578, 61, 60),
 'post58-first-registry-realloc-zero': (166767, 0, 514, 1020, 119, 114),
 'extended119-tls-publication-false': (168635, 0, 515, 1024, 119, 115),
 'extended119-first-local-allocation-zero': (25243, 1, 147, 298, 34, 34)}
STATIC_EXTENDED_CONTROL_COUNTS = {'entry-reentry': (4021, 1, 5, 3, 0, 0),
 'return-reentry': (4046, 1, 5, 4, 0, 0),
 'entry-owner': (4021, 1, 5, 3, 0, 0),
 'return-owner': (4046, 1, 5, 4, 0, 0),
 'entry-table': (5990, 1, 21, 41, 5, 5),
 'return-table': (6015, 1, 21, 42, 5, 5)}
STATIC_EXTENDED_STATE_IDENTITIES = {'extended119-clean': '6658a977b892d559a2130fe2286e499254f967d7e4534cdbcb943713bd7c23bc',
 'extended119-nested-fs-dirty': '6658a977b892d559a2130fe2286e499254f967d7e4534cdbcb943713bd7c23bc',
 'extended119-cursor-false': '6658a977b892d559a2130fe2286e499254f967d7e4534cdbcb943713bd7c23bc',
 'extended120-observational-prefix': '87d45eb90cc77f23520ec96177bcd728dcb13b279298c9c52415caee2be4dd0b',
 'string-range-malloc-before-effect-stop': '3b42ddc816171e9e2f15548b3d8a5067ae367a6728ef71185af8379b9d032590',
 'string-range-malloc-after-effect-stop': '3b42ddc816171e9e2f15548b3d8a5067ae367a6728ef71185af8379b9d032590',
 'string-range-malloc-zero-original-mode4': 'eae2f6ee999ac2a6f888709ec781513733c97450e557cf9c8125cb725e4d06b1',
 'post58-registry-growth-before-effect-stop': 'fc2f7df9c4148dabe16c67be6b4bae3a1fd8b1b5964dff6b8cf4076e80719350',
 'post58-registry-growth-after-effect-stop': 'fc2f7df9c4148dabe16c67be6b4bae3a1fd8b1b5964dff6b8cf4076e80719350',
 'post58-first-registry-realloc-zero': 'bb0b380b7e35ee48de3a77e7168cdbbf2c77babb432fe1bfdb53f94d5b62201a',
 'extended119-tls-publication-false': '2fd648b531fe99376a1ce6b776b1b284d3134aae3d56490f5aadfb9a38facc70',
 'extended119-first-local-allocation-zero': '52f8f58849fc17bf787de5b2d2454e956f411b1476a1b170b6a77663226d8b24',
 'entry-reentry': '8e0663e459b686ef68b0a794c4c4718c972d5f20281f339a714033f8535e2493',
 'return-reentry': 'd7a7f9b88fb1085fb55398eb3a53a3c12767c0e2bb4514e0d40960c2dad66566',
 'entry-owner': '8e0663e459b686ef68b0a794c4c4718c972d5f20281f339a714033f8535e2493',
 'return-owner': 'd7a7f9b88fb1085fb55398eb3a53a3c12767c0e2bb4514e0d40960c2dad66566',
 'entry-table': '43089e05987a68bf94901163eec863ef6718390606ea0ed1537d7a8d2c60f66b',
 'return-table': '75d921612a430bd1d9f43646d711a09ee4d2a6d58b70d81cbdaca7466f8ba8d6'}
STATIC_EXTENDED_SCOPE_IDENTITIES = {'extended119-clean': '52c790c43cc3eefe606c8ba02a9bfc11e760008223355f53c2713db07687e46f',
 'extended119-nested-fs-dirty': '52c790c43cc3eefe606c8ba02a9bfc11e760008223355f53c2713db07687e46f',
 'extended119-cursor-false': '52c790c43cc3eefe606c8ba02a9bfc11e760008223355f53c2713db07687e46f',
 'extended120-observational-prefix': '4b87927e0d4f223c33665544404e7109cb0a2ac942da39e4b96c5de1b41e6450',
 'string-range-malloc-before-effect-stop': 'd88b62e2ff8c8f57458619caeb66d862fbb0b29a1963f966519253a4ad74e159',
 'string-range-malloc-after-effect-stop': 'd88b62e2ff8c8f57458619caeb66d862fbb0b29a1963f966519253a4ad74e159',
 'string-range-malloc-zero-original-mode4': '1e81a87ab0803d099d8b6bb02618e602686a463303f1613ed6708e4af3103335',
 'post58-registry-growth-before-effect-stop': '0ed991e9f803a8c316beed809966966918dcf07eddc94eabd3630de4f0f1fb2e',
 'post58-registry-growth-after-effect-stop': '0ed991e9f803a8c316beed809966966918dcf07eddc94eabd3630de4f0f1fb2e',
 'post58-first-registry-realloc-zero': '6c4bd18a421f42f0375f0f2aaef8126c94653c2959320ecb6d11f54e3c8ae25e',
 'extended119-tls-publication-false': '0250eaa4ae1a142ef93eaf9933fda3bb69b433d52d3f9e718f5e61941dca45a5',
 'extended119-first-local-allocation-zero': 'cf1b74714d169dda0dd662eacaf0730620d8b7eb5f218a9104e115bb1ee82324',
 'entry-reentry': '294da0ef44ba1efd33fefaa95073bd3db3d56400db7af340acd7f8f447b325ec',
 'return-reentry': 'd5014ee72e9c8abab4f9929b1a209aadc2ca0ea62e9435014c9a98e9f739db7c',
 'entry-owner': '294da0ef44ba1efd33fefaa95073bd3db3d56400db7af340acd7f8f447b325ec',
 'return-owner': 'd5014ee72e9c8abab4f9929b1a209aadc2ca0ea62e9435014c9a98e9f739db7c',
 'entry-table': '8e37dcc84365697b35051e54f6d8a8d517895c278b5bba4154704de3e7316c99',
 'return-table': 'e2b8772cc58223475c8eae1870dc40a98a20ca43e2f2a287c4a8076d0cb16aa3'}
STATIC_EXTENDED_TOTAL_CHECKS = 1460749
STATIC_EXTENDED_TOTAL_STATES = 19536

STATIC_LIST_COUNTS = {'list133-clean': (209275, 0, 559, 1196, 133, 123),
 'list133-nested-fs-dirty': (209285, 0, 559, 1196, 133, 123),
 'list133-cursor-false': (209283, 0, 559, 1196, 133, 123),
 'list134-observational-prefix': (209712, 1, 559, 1201, 133, 123),
 'named-message-return-zero': (209273, 0, 559, 1196, 133, 123),
 'named-message-before-effect-stop': (194019, 1, 539, 1132, 126, 117),
 'named-message-after-effect-stop': (194020, 1, 539, 1132, 126, 117),
 'named-message-preexisting-same-name': (209275, 0, 559, 1196, 133, 123),
 'named-message-preexisting-other-name': (209275, 0, 559, 1196, 133, 123),
 'list133-string-range-zero-original-mode4': (206622, 0, 559, 1178, 133, 123),
 'list133-tls-publication-false': (235533, 0, 597, 1270, 133, 123),
 'list133-first-local-allocation-zero': (26418, 1, 147, 298, 34, 34),
 'post119-registry-growth-after-effect-stop': (179242, 1, 525, 1056, 121, 116),
 'post119-first-registry-realloc-zero': (209703, 0, 561, 1196, 133, 122)}
STATIC_LIST_CONTROL_COUNTS = {'entry-reentry': (4296, 1, 5, 3, 0, 0),
 'return-reentry': (4323, 1, 5, 4, 0, 0),
 'entry-owner': (4296, 1, 5, 3, 0, 0),
 'return-owner': (4323, 1, 5, 4, 0, 0),
 'entry-table': (6407, 1, 21, 41, 5, 5),
 'return-table': (6434, 1, 21, 42, 5, 5)}
STATIC_LIST_STATE_IDENTITIES = {'list133-clean': 'b02d2dec91ad8d8ab3cf8d81d1f2944078f7b20dc0803d8882858d4cefc0b8b2',
 'list133-nested-fs-dirty': 'b02d2dec91ad8d8ab3cf8d81d1f2944078f7b20dc0803d8882858d4cefc0b8b2',
 'list133-cursor-false': 'b02d2dec91ad8d8ab3cf8d81d1f2944078f7b20dc0803d8882858d4cefc0b8b2',
 'list134-observational-prefix': 'ed2f4373c21aae64261dfa9336506c3475ab6b5b4cbcfe880f8b04fc87320a03',
 'named-message-return-zero': 'b02d2dec91ad8d8ab3cf8d81d1f2944078f7b20dc0803d8882858d4cefc0b8b2',
 'named-message-before-effect-stop': 'db3821d15385f9c17c34c7422b88e5e29ddfc09baed7f6cfaec9a5203a54f8d8',
 'named-message-after-effect-stop': 'db3821d15385f9c17c34c7422b88e5e29ddfc09baed7f6cfaec9a5203a54f8d8',
 'named-message-preexisting-same-name': 'b02d2dec91ad8d8ab3cf8d81d1f2944078f7b20dc0803d8882858d4cefc0b8b2',
 'named-message-preexisting-other-name': 'b02d2dec91ad8d8ab3cf8d81d1f2944078f7b20dc0803d8882858d4cefc0b8b2',
 'list133-string-range-zero-original-mode4': '522d62cf3c0e9cb46251bfa3e9582b3c7a2b2bbee2c8a6db2d38c494465e7e1f',
 'list133-tls-publication-false': '09a3b9cbf8a045d75aa751e6166b4396da2c5dc496df025bfdf0e69506f44463',
 'list133-first-local-allocation-zero': 'a093e62177570e4b1c7302fbf90be677f68c58e066a2a622dd01dc196fba1266',
 'post119-registry-growth-after-effect-stop': '864be707e95f62e8962f4829be1747d3f9bf8df94d8acfa6a508faf2ec5808d3',
 'post119-first-registry-realloc-zero': '5088eda7a825b3c9b9c935d02c8649832eab9fc63a571f584a5d53bd97bbfb8a',
 'entry-reentry': 'a007156f02ce3511fed7fa4e4fbeb8ec838295064304e742642db95a72c83501',
 'return-reentry': '0cc87aa0c9c2490eb631c0ae646ab7f30283123d6ebc2d82f7eb5252957ba866',
 'entry-owner': 'a007156f02ce3511fed7fa4e4fbeb8ec838295064304e742642db95a72c83501',
 'return-owner': '0cc87aa0c9c2490eb631c0ae646ab7f30283123d6ebc2d82f7eb5252957ba866',
 'entry-table': 'a55e5c210edca25d2bded50ed74020e6dc4504950b4169a4d04e3a10430fb770',
 'return-table': 'a9053779ca9a3f272b3daf1edd60a5f7a977b33b60fefe463672a6880cbc75a6'}
STATIC_LIST_SCOPE_IDENTITIES = {'list133-clean': '32582e44dd4b469c46a594edb4bded89e120648e07cb6e57cb7f92c51617bcca',
 'list133-nested-fs-dirty': '32582e44dd4b469c46a594edb4bded89e120648e07cb6e57cb7f92c51617bcca',
 'list133-cursor-false': '32582e44dd4b469c46a594edb4bded89e120648e07cb6e57cb7f92c51617bcca',
 'list134-observational-prefix': '2ab48660064ae40e73daba4f150dcb9dc6e3d73e225d92b05ca461f8de531dbf',
 'named-message-return-zero': '32582e44dd4b469c46a594edb4bded89e120648e07cb6e57cb7f92c51617bcca',
 'named-message-before-effect-stop': 'd13548d8889b364f3f16c4b80ffcdf6cd3d6945a2d8ee586e129f8c8a07af01f',
 'named-message-after-effect-stop': 'd13548d8889b364f3f16c4b80ffcdf6cd3d6945a2d8ee586e129f8c8a07af01f',
 'named-message-preexisting-same-name': '32582e44dd4b469c46a594edb4bded89e120648e07cb6e57cb7f92c51617bcca',
 'named-message-preexisting-other-name': '32582e44dd4b469c46a594edb4bded89e120648e07cb6e57cb7f92c51617bcca',
 'list133-string-range-zero-original-mode4': '6830a2aa750ebd585af8ad2108c6c641db954bca13335f18f81908c39bef8331',
 'list133-tls-publication-false': '795948b4afa337fa4e80cd168869a109f78787f35e0263e613b6e75fc72bec63',
 'list133-first-local-allocation-zero': 'dc13b8bbd38bbe6d593ae31d265e8c74bdc810738e6c5099f688b0e126c7d572',
 'post119-registry-growth-after-effect-stop': '87b64f6c822e185047bfcd1b5f8aa7b3736f7e54c84df30e483ad2cdec2f3eef',
 'post119-first-registry-realloc-zero': 'f4afbaab4d803fc9edcb036dee77c69f9da0e94c6748ba97673e8000377e3cc4',
 'entry-reentry': '1a05d91727d9544d04f98c33127cfd9dd97a4ac4d93ce8d0c9687a0dbfe48259',
 'return-reentry': '25b6e87c5a72e03141904855f2101f701bebedee030f9ef56032f0669db2cb42',
 'entry-owner': '1a05d91727d9544d04f98c33127cfd9dd97a4ac4d93ce8d0c9687a0dbfe48259',
 'return-owner': '25b6e87c5a72e03141904855f2101f701bebedee030f9ef56032f0669db2cb42',
 'entry-table': 'f221419be8bda6755b722b5d393e1b92e73466a2bd8d5003a0e4634443df0f89',
 'return-table': 'f4cc172e1991e51b9f53c01617820c23e26b4906ed7c65197b1a5c68f694610a'}
STATIC_LIST_TOTAL_CHECKS = 2741014
STATIC_LIST_TOTAL_STATES = 30654

STATIC_FINAL_COUNTS = {'final144-clean': (237415, 0, 595, 1268, 144, 126),
 'final144-dirty-below-threshold-cursor-false': (237423, 0, 595, 1268, 144, 126),
 'final144-zero-platform-results': (237387, 0, 595, 1268, 144, 126),
 'final144-live-dc-release-zero-caps-zero': (237411, 0, 595, 1268, 144, 126),
 'final144-wheel-highbit-four': (237422, 0, 595, 1268, 144, 126),
 'final144-wheel-three-preexisting-wheel': (237422, 0, 595, 1268, 144, 126),
 'final144-wheel-highbit-low16-not-four': (237415, 0, 595, 1268, 144, 126),
 'final144-wheel-low16-not-three': (237122, 0, 594, 1268, 144, 126),
 'final144-message-return-zero': (237418, 0, 595, 1268, 144, 126),
 'final144-string-range-zero-original-mode4': (234564, 0, 595, 1250, 144, 126),
 'final144-tls-publication-false': (271124, 0, 640, 1356, 144, 126),
 'final144-first-local-allocation-zero': (28181, 1, 147, 298, 34, 34),
 'final144-post119-registry-growth-after-effect-stop': (185565, 1, 525, 1056, 121, 116),
 'final144-post119-first-registry-realloc-zero': (237841, 0, 597, 1268, 144, 125),
 'final144-process-version-before-effect-stop': (217254, 1, 561, 1202, 133, 123),
 'final144-process-version-after-effect-stop': (217254, 1, 561, 1202, 133, 123),
 'final144-dc-acquire-before-effect-stop': (218734, 1, 566, 1202, 133, 123),
 'final144-dc-acquire-after-effect-stop': (218734, 1, 566, 1202, 133, 123),
 'final144-dc-release-before-effect-stop': (219617, 1, 569, 1202, 133, 123),
 'final144-dc-release-after-effect-stop': (219617, 1, 569, 1202, 133, 123),
 'final144-brush15-before-effect-stop': (221389, 1, 575, 1202, 133, 123),
 'final144-brush15-after-effect-stop': (221389, 1, 575, 1202, 133, 123),
 'final144-cursor32514-before-effect-stop': (221980, 1, 577, 1202, 133, 123),
 'final144-cursor32514-after-effect-stop': (221980, 1, 577, 1202, 133, 123),
 'final144-wheel-message-before-effect-stop': (225655, 1, 584, 1212, 135, 124),
 'final144-wheel-message-after-effect-stop': (225656, 1, 584, 1212, 135, 124)}
STATIC_FINAL_CONTROL_COUNTS = {'entry-reentry': (4450, 1, 5, 3, 0, 0),
 'return-reentry': (4480, 1, 5, 4, 0, 0),
 'entry-owner': (4450, 1, 5, 3, 0, 0),
 'return-owner': (4480, 1, 5, 4, 0, 0),
 'entry-table': (6774, 1, 21, 41, 5, 5),
 'return-table': (6804, 1, 21, 42, 5, 5)}
STATIC_FINAL_STATE_IDENTITIES = {'final144-clean': '39c56580fc97333cdc76f5a3dbc07d96b0ec3d4b8b0b4ca2c546a68f69491935',
 'final144-dirty-below-threshold-cursor-false': 'c4207d752cc1e7a537dcd2d5ec731829146e834be2676f563bd7bcb5e8a60836',
 'final144-zero-platform-results': 'c4207d752cc1e7a537dcd2d5ec731829146e834be2676f563bd7bcb5e8a60836',
 'final144-live-dc-release-zero-caps-zero': '39c56580fc97333cdc76f5a3dbc07d96b0ec3d4b8b0b4ca2c546a68f69491935',
 'final144-wheel-highbit-four': '7ae776150e7d25f50bdc552ecc53edb0dbeed277fc5c9cba3f22bc0e4f5bd869',
 'final144-wheel-three-preexisting-wheel': '1e649b4824349461cef15bc34f1d667a467ca616e8d9db4beca5ef84993502e4',
 'final144-wheel-highbit-low16-not-four': 'f6adb33ebed1de18cc2fee28e17605f0a5e72dd82826ac621982fa0da709f2eb',
 'final144-wheel-low16-not-three': 'f6402fe284fa7202281890ab6f138f9fd724ceb1e2d3b68216fbc5a01e7ab7f1',
 'final144-message-return-zero': '7ae776150e7d25f50bdc552ecc53edb0dbeed277fc5c9cba3f22bc0e4f5bd869',
 'final144-string-range-zero-original-mode4': '57a9679169ddfd178054c8656b1992e8f00d38fdd32cdcd67e4b6b50b0b1e399',
 'final144-tls-publication-false': '6307cdb0ca506b407cc6abdaea18845f7273fa1b89fabbe5762fae585a55c745',
 'final144-first-local-allocation-zero': 'd9ffc40682d060076abe94de2fed7c8c26a695969ad79dab0a27f05dabfd63d0',
 'final144-post119-registry-growth-after-effect-stop': '42a92588bf60e9fcfde4a37a470ebfc16f85525dccc2be2eff73fe04f509bca6',
 'final144-post119-first-registry-realloc-zero': '3e2df8e899c13377ac6bcb4b5a4c84b32cfaf0376355d9d62353490cc87dd80c',
 'final144-process-version-before-effect-stop': '5fdf4dd6ed2ecb965dbfe63759abe0c6e9f851f938659adc4726ce4d4c51a57f',
 'final144-process-version-after-effect-stop': '5fdf4dd6ed2ecb965dbfe63759abe0c6e9f851f938659adc4726ce4d4c51a57f',
 'final144-dc-acquire-before-effect-stop': '039563c592802dcdc07c653be564d7ca2585c069773e777669816b0b8e5b8b8e',
 'final144-dc-acquire-after-effect-stop': '039563c592802dcdc07c653be564d7ca2585c069773e777669816b0b8e5b8b8e',
 'final144-dc-release-before-effect-stop': 'eb9e41b0d40cd8e49187bd8606930a62b9e64db71300112585614030d1bf5c10',
 'final144-dc-release-after-effect-stop': 'eb9e41b0d40cd8e49187bd8606930a62b9e64db71300112585614030d1bf5c10',
 'final144-brush15-before-effect-stop': 'bb0422ed02559b7abae9791025e53cdd4c3f6d153ceddcb63b9db8e92667af16',
 'final144-brush15-after-effect-stop': 'bb0422ed02559b7abae9791025e53cdd4c3f6d153ceddcb63b9db8e92667af16',
 'final144-cursor32514-before-effect-stop': '016c98b0d5891eda711b617f5e9a8f854f8b149228e8639bd40ab36fc0e29496',
 'final144-cursor32514-after-effect-stop': '016c98b0d5891eda711b617f5e9a8f854f8b149228e8639bd40ab36fc0e29496',
 'final144-wheel-message-before-effect-stop': '41c83f677db7e6a51960ca68da23b21f93472fdab172f730d6d92aef48ab3843',
 'final144-wheel-message-after-effect-stop': '41c83f677db7e6a51960ca68da23b21f93472fdab172f730d6d92aef48ab3843',
 'entry-reentry': '17a2fe2c47a522ccbaa33b04383142ec61000ae45ec8dcca16d6f4812545c0fd',
 'return-reentry': '755756f2f9792fdc098c829b961950d0ac2aa1604c994fa89f70016eecddf548',
 'entry-owner': '17a2fe2c47a522ccbaa33b04383142ec61000ae45ec8dcca16d6f4812545c0fd',
 'return-owner': '755756f2f9792fdc098c829b961950d0ac2aa1604c994fa89f70016eecddf548',
 'entry-table': '4ecc498834f72ae5cd610435515f1747bf5cf00c8c3680563a1e9a5449416a11',
 'return-table': 'f8201ae51dd1b39ea9553573478dea13de41a21acdddea97c8451ef38e2db5ed'}
STATIC_FINAL_SCOPE_IDENTITIES = {'final144-clean': 'c60e86e0c44a8116722183993b0c3274f8ee245706be80313dfed38ba84aeb97',
 'final144-dirty-below-threshold-cursor-false': 'c60e86e0c44a8116722183993b0c3274f8ee245706be80313dfed38ba84aeb97',
 'final144-zero-platform-results': 'c60e86e0c44a8116722183993b0c3274f8ee245706be80313dfed38ba84aeb97',
 'final144-live-dc-release-zero-caps-zero': 'c60e86e0c44a8116722183993b0c3274f8ee245706be80313dfed38ba84aeb97',
 'final144-wheel-highbit-four': 'c60e86e0c44a8116722183993b0c3274f8ee245706be80313dfed38ba84aeb97',
 'final144-wheel-three-preexisting-wheel': '96a57b5c31c00c105be8d0a8f36b73cbc939ee49b703ca978dc2026f830168d1',
 'final144-wheel-highbit-low16-not-four': 'c60e86e0c44a8116722183993b0c3274f8ee245706be80313dfed38ba84aeb97',
 'final144-wheel-low16-not-three': '5a460546696ae0212451cc1258b3523e46571c0c8f1d07c53eeb3710b0520c80',
 'final144-message-return-zero': 'c60e86e0c44a8116722183993b0c3274f8ee245706be80313dfed38ba84aeb97',
 'final144-string-range-zero-original-mode4': '20f4a09b9908f5dac3385555009727f5f71ff5074b481b7b9ddeab8d5e466529',
 'final144-tls-publication-false': 'dbc3a0eb6480765008acbbbed0d3b3b96adaf268fae13b9665b6636e5f028b2c',
 'final144-first-local-allocation-zero': 'caf782fb027011dec5edcc8c0c4a47b7e72af87e8cc7e7d43503dea3f651dee4',
 'final144-post119-registry-growth-after-effect-stop': 'c01a8d604c1231a4a81b8537e674ff2b3819fb45015fbec0f6bbc5c524b3f81d',
 'final144-post119-first-registry-realloc-zero': '542f26b9f81f9f638b9fa599713982c7287831f9e6766c04cdbdf1d0a51550c7',
 'final144-process-version-before-effect-stop': 'b1a518adf4ae9d9b9ee4f7ff0efd4ef7edec64e37da1ea4db0c970c088ce19ce',
 'final144-process-version-after-effect-stop': 'b1a518adf4ae9d9b9ee4f7ff0efd4ef7edec64e37da1ea4db0c970c088ce19ce',
 'final144-dc-acquire-before-effect-stop': '8e97491019ae26e1cda7140d1a74142f7fad30972d127835a94f408e467fea82',
 'final144-dc-acquire-after-effect-stop': '8e97491019ae26e1cda7140d1a74142f7fad30972d127835a94f408e467fea82',
 'final144-dc-release-before-effect-stop': '4cabc035a8052e245a3c36215bdbbee7a0b92845a5ce0e2c8c925b7a489b315d',
 'final144-dc-release-after-effect-stop': '4cabc035a8052e245a3c36215bdbbee7a0b92845a5ce0e2c8c925b7a489b315d',
 'final144-brush15-before-effect-stop': '0afbfbd40faffb8997cc7f3606ca76c6bd9ddba3c2deb13cb10ab98ff633293d',
 'final144-brush15-after-effect-stop': '0afbfbd40faffb8997cc7f3606ca76c6bd9ddba3c2deb13cb10ab98ff633293d',
 'final144-cursor32514-before-effect-stop': 'a8c6de148390966c06e9b5df1461098ea8878ffc8e4230ca990c01ec67d0cf99',
 'final144-cursor32514-after-effect-stop': 'a8c6de148390966c06e9b5df1461098ea8878ffc8e4230ca990c01ec67d0cf99',
 'final144-wheel-message-before-effect-stop': '8dde916514af8aa95d2610026fa0cbf3d535fa92d0081b38be61b378f4097fa8',
 'final144-wheel-message-after-effect-stop': '8dde916514af8aa95d2610026fa0cbf3d535fa92d0081b38be61b378f4097fa8',
 'entry-reentry': '14c8a4de63dd05a6802b71130bf94dfc14970db7be791403cb4b97ebf15cbcb6',
 'return-reentry': '98ab0c761ff249fab277522f5482db803afa08bfece1c9a79c5c3ab48d8f2dd2',
 'entry-owner': '14c8a4de63dd05a6802b71130bf94dfc14970db7be791403cb4b97ebf15cbcb6',
 'return-owner': '98ab0c761ff249fab277522f5482db803afa08bfece1c9a79c5c3ab48d8f2dd2',
 'entry-table': 'ac18932547c18d0d15c72ab4c6b0233903b851a1e35335be0104f730216a3e1b',
 'return-table': '27e6d08b4612f2214cf514c0303a15d07b9abd67c4153b7219e6894ad9fa8258'}
STATIC_FINAL_TOTAL_CHECKS = 5774407
STATIC_FINAL_TOTAL_STATES = 60791

STATIC_CHECKS = ('static_startup_prefix', 'static_startup_three', 'static_startup_seven', 'static_startup_fifteen', 'static_startup_thirtyfour', 'static_startup_application', 'static_startup_extended', 'static_startup_list', 'static_startup_final')


def static_spec(version=1):
    if type(version) is not int or version not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        raise ValueError('unsupported static reference version')
    if version == 9:
        return dict(reference=STATIC_FINAL_REFERENCE,digest=STATIC_FINAL_REFERENCE_SHA256,
            schema='claw-original-static-startup-final-records-pages-v9',command='static-startup-final',
            counts=STATIC_FINAL_COUNTS,identities=STATIC_FINAL_STATE_IDENTITIES,
            checks=STATIC_FINAL_TOTAL_CHECKS,states=STATIC_FINAL_TOTAL_STATES,
            seed='final144-clean',report_prefix='static-final-native-',controls=STATIC_SEVEN_CONTROLS,
            count_fields=('checks','honest_stops','physical_events','static_boundaries','wrappers','registrations'),
            additional_references={},scope_identities=STATIC_FINAL_SCOPE_IDENTITIES,
            scope_fields=STATIC_SCOPE_FIELDS+('reference_only_physical_event_indices',),
            control_counts=STATIC_FINAL_CONTROL_COUNTS)
    if version == 8:
        return dict(reference=STATIC_LIST_REFERENCE,digest=STATIC_LIST_REFERENCE_SHA256,
            schema='claw-original-static-startup-list-records-pages-v8',command='static-startup-list',
            counts=STATIC_LIST_COUNTS,identities=STATIC_LIST_STATE_IDENTITIES,
            checks=STATIC_LIST_TOTAL_CHECKS,states=STATIC_LIST_TOTAL_STATES,
            seed='list133-clean',report_prefix='static-list-native-',controls=STATIC_SEVEN_CONTROLS,
            count_fields=('checks','honest_stops','physical_events','static_boundaries','wrappers','registrations'),
            additional_references={},scope_identities=STATIC_LIST_SCOPE_IDENTITIES,
            scope_fields=STATIC_SCOPE_FIELDS+('reference_only_physical_event_indices',),
            control_counts=STATIC_LIST_CONTROL_COUNTS)
    if version == 7:
        return dict(reference=STATIC_EXTENDED_REFERENCE,digest=STATIC_EXTENDED_REFERENCE_SHA256,
            schema='claw-original-static-startup-extended-records-pages-v7',command='static-startup-extended',
            counts=STATIC_EXTENDED_COUNTS,identities=STATIC_EXTENDED_STATE_IDENTITIES,
            checks=STATIC_EXTENDED_TOTAL_CHECKS,states=STATIC_EXTENDED_TOTAL_STATES,
            seed='extended119-clean',report_prefix='static-extended-native-',controls=STATIC_SEVEN_CONTROLS,
            count_fields=('checks','honest_stops','physical_events','static_boundaries','wrappers','registrations'),
            additional_references={},scope_identities=STATIC_EXTENDED_SCOPE_IDENTITIES,
            scope_fields=STATIC_SCOPE_FIELDS+('reference_only_physical_event_indices',),
            control_counts=STATIC_EXTENDED_CONTROL_COUNTS)
    if version == 6:
        return dict(reference=STATIC_APPLICATION_REFERENCE,digest=STATIC_APPLICATION_REFERENCE_SHA256,
            schema='claw-original-static-startup-application-shared-pages-v6',command='static-startup-application',
            counts=STATIC_APPLICATION_COUNTS,identities=STATIC_APPLICATION_STATE_IDENTITIES,
            checks=STATIC_APPLICATION_TOTAL_CHECKS,states=STATIC_APPLICATION_TOTAL_STATES,
            seed='joint58-clean',report_prefix='static-application-native-',controls=STATIC_SEVEN_CONTROLS,
            count_fields=('checks','honest_stops','physical_events','static_boundaries','wrappers','registrations'),
            additional_references={},scope_identities=STATIC_APPLICATION_SCOPE_IDENTITIES,
            scope_fields=STATIC_SCOPE_FIELDS+('reference_only_physical_event_indices',),
            control_counts=STATIC_APPLICATION_CONTROL_COUNTS)
    index = version - 1
    return dict(reference=(STATIC_REFERENCE, STATIC_THREE_REFERENCE, STATIC_SEVEN_REFERENCE, STATIC_FIFTEEN_REFERENCE, STATIC_THIRTYFOUR_REFERENCE)[index],
        digest=(STATIC_REFERENCE_SHA256, STATIC_THREE_REFERENCE_SHA256, STATIC_SEVEN_REFERENCE_SHA256, STATIC_FIFTEEN_REFERENCE_SHA256, STATIC_THIRTYFOUR_REFERENCE_SHA256)[index],
        schema=('claw-original-static-startup-prefix-pages-v1', 'claw-original-static-startup-three-wrapper-pages-v2', 'claw-original-static-startup-seven-wrapper-pages-v3', 'claw-original-static-startup-fifteen-wrapper-pages-v4', 'claw-original-static-startup-thirtyfour-wrapper-pages-v5')[index],
        command=('static-startup-prefix', 'static-startup-three', 'static-startup-seven', 'static-startup-fifteen', 'static-startup-thirtyfour')[index],
        counts=(STATIC_COUNTS, STATIC_THREE_COUNTS, STATIC_SEVEN_COUNTS, STATIC_FIFTEEN_COUNTS, STATIC_THIRTYFOUR_COUNTS)[index],
        identities=(STATIC_STATE_IDENTITIES, STATIC_THREE_STATE_IDENTITIES, STATIC_SEVEN_STATE_IDENTITIES, STATIC_FIFTEEN_STATE_IDENTITIES, STATIC_THIRTYFOUR_STATE_IDENTITIES)[index],
        checks=(11976, 15183, 26569, 50907, 167431)[index], states=(217, 317, 694, 1415, 4404)[index],
        seed=('two-wrappers-seed0', 'three-wrappers-seed0', 'seven-wrappers-seed0', 'fifteen-wrappers-seed0', 'thirtyfour-wrappers-seed0')[index],
        report_prefix=('static-tail-native-', 'static-lock-native-', 'static-seven-native-', 'static-fifteen-native-', 'static-thirtyfour-native-')[index],
        controls=STATIC_CONTROLS if version < 3 else STATIC_SEVEN_CONTROLS,
        count_fields=('checks','honest_stops','physical_events','static_boundaries','wrappers') + (('registrations',) if version == 5 else ()),
        additional_references={STATIC_THIRTYFOUR_INTERPRETATION:STATIC_THIRTYFOUR_INTERPRETATION_SHA256} if version == 5 else {},
        scope_identities=STATIC_THIRTYFOUR_SCOPE_IDENTITIES if version == 5 else STATIC_FIFTEEN_SCOPE_IDENTITIES if version == 4 else None,
        control_counts=STATIC_THIRTYFOUR_CONTROL_COUNTS if version == 5 else STATIC_FIFTEEN_CONTROL_COUNTS if version == 4 else {action: ((2778,1,21,41,5) if action == 'entry-table' else (2798,1,21,42,5)) if action.endswith('-table') else
            (((1107,1132,1180)[index],1,5,3,0) if action.startswith('entry') else ((1127,1152,1200)[index],1,5,4,0))
            for action in (STATIC_CONTROLS if version < 3 else STATIC_SEVEN_CONTROLS)})


def static_certificate_version(payload):
    return {'static-startup-prefix': 1, 'static-startup-three': 2, 'static-startup-seven': 3, 'static-startup-fifteen': 4, 'static-startup-thirtyfour': 5, 'static-startup-application': 6, 'static-startup-extended': 7, 'static-startup-list': 8, 'static-startup-final': 9}.get(payload.get('command'), 1)

CRT_REFERENCE = 'work/native-crt-exit-registry-check/frozen-v1/provenance.json'
CRT_REFERENCE_SHA256 = '45c1fb281c84cd54a5adbd891177f1c79d551b5dc42be917e3ec80c2ce5a4e84'

# Counters and outcome fingerprints from the complete recorded whole-leaf replay.
CRT_COUNT_FIELDS = ('roots', 'leaf_roots', 'physical_events', 'observed_source_entries', 'reference_only_entries', 'reference_only_internal_entries', 'reference_entries_after_native_stop', 'compared_reference_states', 'observations')
CRT_PROFILES = {
    'inplace126': ('7e597fca619f022fc8c2772ce480e7ca8f9a1d355ed8e937f9938d5af5b386ce',
        (128, 126, 431, 506, 378, 378, 0, 1874, 1874), 44470,
        'aa13c51a06b9179197fe87ab3759af078dd98f48989aaec0b7587ca45afe9628'),
    'moving126': ('3daf24d65970ba3f054da02a3346bda0793a98dd7da74db78ae1fa344f966a51',
        (128, 126, 431, 506, 378, 378, 0, 1874, 1874), 61304,
        '65cf15c322a0e719a2c3c62a58610b09d7e00102f6cdad0041a9811c3c9979cb'),
    'mixed126': ('c62345054649dad5b79aada52385022e666226578c2bca80af5cb88d64a6a787',
        (128, 126, 431, 506, 378, 378, 0, 1874, 1874), 52410,
        '81bbedf04223c85b8ab30b45b38f024f28b6a78186df1006f20a6df9a9492f9c'),
    'resize-fail-retry': ('a9ab5114e5d0f99593406ffe6d34853f463e41a47025c01593adf6a716505080',
        (129, 127, 436, 510, 381, 381, 0, 1892, 1892), 44638,
        'ab3d031c463886c8dab2a40786a105a060e5cf467ac38874ae8fc513ea6fb871'),
    'moving-late-fail-retry': ('4adcb07fe42766c25e0f941feac02b3d92bdc48f9b01555ae28d35a8ce1be14b',
        (129, 127, 436, 510, 381, 381, 0, 1892, 1892), 62120,
        'fe1ee78616a83edbdae5ea5ab33e5449bcae71672e65f3a7dffd4a6ac4b5d259'),
    'null-callback': ('e53952b6253b39b31088facc75f77a28e9f949882d93288707c1d2990fda3500',
        (3, 0, 8, 5, 3, 3, 0, 26, 26), 1360,
        '36019f42916e18d5fb9b58d3b5be17c2ed44fb4e821132159c806610501e994e'),
    'first-allocation-failure': ('c2f57440f2b47c6d7730cab4c6363142ec46510ec41296041f073a6c41788c5c',
        (2, 0, 5, 3, 8, 0, 8, 14, 15), 1105,
        '48dd1a7e69497658865a1fea6f56b5e737ad8bfaf7ad98373aa74dd797d49ba8'),
    'physical-prefix-1': ('f4ab3e51b1b7a6d352fe0467ae9e49979abdde37e49b7d8e93004b739183ffe9',
        (1, 0, 1, 1, 0, 0, 0, 3, 4), 842,
        '48fd2be5d15d80d8f3d59da04b9261d9c59e48df0c726790d1c26d7344e9d548'),
    'physical-prefix-4': ('40f2a3a02ad80b560ea3206a05e65bc31abec0c473a62cf9cb25e79081d82d7e',
        (1, 0, 4, 1, 0, 0, 0, 9, 10), 977,
        '60a62ee5ec7a905cf335d9c41d1de01961167326dd5e0841f12afe53ec48a0b9'),
    'physical-prefix-5': ('5f03a2b0fbd227feb800017e20ed7f681280c68c991e56be9f875bb18843d9e3',
        (2, 0, 5, 2, 0, 0, 0, 13, 14), 1067,
        '22fe76749c81e85846dc564a922e466b825ed435baaf7a917f977bc037725a25'),
    'physical-prefix-6': ('1fae07367de75601abafeaea55844ebdfa64a8755fd5d87b6ab5cf010c6b96a7',
        (3, 1, 6, 5, 2, 2, 0, 19, 22), 1255,
        '09c09b071e161dc6dfc4c7b9996682e5a1163e87ed856a482e5da226ab4facda'),
    'physical-prefix-8': ('c2273be96250c19f4860ad15f66217b67d1b24affead0b8b286b418720d6cb9a',
        (3, 1, 8, 6, 3, 3, 0, 25, 28), 1397,
        'ee78a13639d48bc1d0fd59caaeda66ed2683566bef0dd614f9233bf26d7702ab'),
    'physical-prefix-71': ('94585a234fdd980c7c37f20093a37ef323d4dca81c57c1887f920742a6490bda',
        (24, 22, 71, 90, 66, 66, 0, 319, 322), 8222,
        'ba1709c09fee541bfbf6cf06aaac7699429c92c90bdec6dc2ba1a48416fd6321'),
    'physical-prefix-105': ('681d2dd462aceee19422e19f2fedbcc7b6548993c03d1541fc0b9edd397471cb',
        (35, 33, 105, 133, 98, 98, 0, 474, 476), 11795,
        'c9ee1c837ce3b9ece35e47dd0e597f1fa8f8c1167588fb5792607a410f4f5b82'),
    'physical-prefix-106': ('6719f164e5392dffc368835a249d009e1ee91e0534c2c48e86a384dd1d45de94',
        (35, 33, 106, 134, 99, 99, 0, 477, 480), 11889,
        '4013e957a30d038ff96c44a611b280e013ee763ea8c9f83a7786b39b1b7ec821'),
    'physical-prefix-107': ('0c145c6ebbe2ac326e565ac64873cb665f67c928b57f3249d676ed35f52588d5',
        (36, 34, 107, 137, 101, 101, 0, 485, 488), 12074,
        '82975d6e17bf6aa1bcb7af7430ff9f32d17dc935603da81a6b12480ae050495e'),
    'fatal-physical-prefix-6': ('6e199d7b1e2d906e475901b1059a16ac9b4cd833a90ec44729e794d09a30fbed',
        (2, 0, 5, 3, 1, 0, 1, 14, 15), 1090,
        '1344d143757736fb25f49b3c1b24ab62ef0a6413799b34a9ce75818953588df2'),
    'fatal-physical-prefix-7': ('95cc936c432d85b828476b422709758cb4070ecccefce3af5c6d5cb3855c6755',
        (2, 0, 5, 3, 2, 0, 2, 14, 15), 1093,
        '0a6ed2fdea29857ff38e573705ee614b05c394cddea95202698d83c93ecb0871'),
    'fatal-physical-prefix-8': ('6199dd302863ee421baea0c69891ab6fbe435f68ab247070483497c7ff043cbe',
        (2, 0, 5, 3, 6, 0, 6, 14, 15), 1098,
        'bd58ff4a0905b33a81de9162b425c64693b4a552b4d1831a9550f02389aa8d38'),
    'fatal-physical-prefix-9': ('0985ec18319f4e36041364325ea66507cfd7aed45a31fb80ae3256a2acefe464',
        (2, 0, 5, 3, 8, 0, 8, 14, 15), 1103,
        'ea37f65260751046c9c5a72232b03d1be01d712c5044af92b6bbb3766266f759'),
    'fatal-physical-prefix-10': ('3e9c63e2788471634088c40249e1f992f5436636e9f490a8fe3718e135028534',
        (2, 0, 5, 3, 8, 0, 8, 14, 15), 1105,
        '844411185002d316d493c6b0bb3a5c2947147f887e1430da6b99cd6f04425776'),
}
MODULE_REFERENCE_SHA256 = '033af968d002ff1763486118aab8736cd69a76f54d8cafda7599de203f320cf8'
EXE = 'Original/claw10/CLAW.EXE'
REZ = 'Original/claw-disc/files/DATA/CLAW.REZ'
FEC = 'work/media/source/CLAW.FEC'
REZ_SHA256 = 'b09802735970de6ee6115259a15af384d09abaed9e80b4107f9e69b7573f4596'
FEC_SHA256 = '9c87c82aaec3c73aa6c9eb268da9db8601aa10f75af35060bff4f1edcfbb80d8'
DEFAULT_CHECK_TIMEOUT = 900
CHECK_TIMEOUTS = {'application_object_source': 7200, 'static_startup_extended': 7200, 'static_startup_list': 7200, 'static_startup_final': 7200}
LIMIT = 'Before/after byte inventories detect net changes, not an atomic repository snapshot or changed-and-restored inputs.'


class PrerequisiteError(ValueError):
    pass


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def select_checks(values=None):
    values = values or [name for name in CHECKS if name not in ('static_startup_list','static_startup_final')]
    if any(value not in CHECKS for value in values):
        raise ValueError('unknown check; choose ' + ', '.join(CHECKS))
    return [name for name in CHECKS if name in values]


def controlled_environment(base, check_dir, check_id=None):
    env = {key: value for key, value in base.items() if not key.startswith('CLAW_')}
    env.update(CLAW_NATIVE_JOBS='1', CLAW_NATIVE_ASAN='1', CLAW_NATIVE_OPTIMIZE='0',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',
               ASAN_OPTIONS='detect_stack_use_after_return=1',
               CLAW_APPLICATION_OBJECT_DIR=str(Path(check_dir).resolve() / 'objects'),
               CLAW_APPLICATION_PREGRAPHICS_CHECK_DIR=str(Path(check_dir).resolve()))
    if check_id in STATIC_CHECKS:
        env['CLAW_NATIVE_STATIC_CHECK_DIR'] = str(Path(check_dir).resolve())
    if check_id == 'crt_registry_source':
        env.update(CLAW_NATIVE_CRT_WHOLE='1', CLAW_NATIVE_CRT_CHECK_DIR=str(Path(check_dir).resolve()))
    return env


def project_membership(root):
    # Match gen_project.tracked_files: index names matter independently of bytes.
    output = subprocess.check_output(['git', 'ls-files', 'Sources', 'App/ClawApp.swift'],
                                     cwd=root, text=True, stderr=subprocess.PIPE, timeout=20)
    return [name for name in output.splitlines() if (Path(root) / name).exists()]


def application_object_shards(root):
    index = Path(root) / APPLICATION_OBJECT_REFERENCE
    if not index.is_file() or digest(index) != APPLICATION_OBJECT_REFERENCE_SHA256:
        raise PrerequisiteError('application object frozen index mismatch or missing')
    data = json.loads(index.read_text())
    if (not isinstance(data, dict) or data.get('schema') != 'claw-original-application-object-shards-v1'
            or data.get('originalSha256') != ORIGINAL_SHA256
            or data.get('profiles') != 61 or data.get('roots') != 62
            or not isinstance(data.get('shards'), list) or len(data['shards']) != 61):
        raise PrerequisiteError('invalid application object frozen index')
    result = {}
    for ordinal, shard in enumerate(data['shards']):
        if (not isinstance(shard, dict) or type(shard.get('index')) is not int
                or shard['index'] != ordinal
                or shard.get('path') != f'profiles/profile-{ordinal:03d}.json.xz'
                or not isinstance(shard.get('sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', shard['sha256'])):
            raise PrerequisiteError('invalid application object shard identity')
        name = str(Path(APPLICATION_OBJECT_REFERENCE).parent / shard['path'])
        result[name] = shard['sha256']
    return result


def crt_registry_shards(root):
    index = Path(root) / CRT_REFERENCE
    if (index.is_symlink() or index.resolve() != Path(root).resolve() / CRT_REFERENCE
            or not index.is_file() or digest(index) != CRT_REFERENCE_SHA256):
        raise PrerequisiteError('CRT frozen provenance mismatch or missing')
    data = json.loads(index.read_text())
    profiles = data.get('profiles') if isinstance(data, dict) else None
    if (not isinstance(data, dict) or data.get('schema') != 'claw-original-crt-exit-registry-pages-v1'
            or data.get('status') != 'PASS' or data.get('programSha256') != ORIGINAL_SHA256
            or not isinstance(profiles, list) or len(profiles) != 21):
        raise PrerequisiteError('invalid CRT frozen provenance')
    result = {}
    names = set()
    for profile in profiles:
        if (not isinstance(profile, dict) or not isinstance(profile.get('name'), str)
                or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', profile['name'])
                or profile['name'] in names or not isinstance(profile.get('path'), str)
                or Path(profile['path']).name != profile['name'] + '.json.gz'
                or '..' in Path(profile['path']).parts
                or not isinstance(profile.get('sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', profile['sha256'])
                or any(type(profile.get(k)) is not int or profile[k] < 0 for k in
                       ('bytes', 'states', 'pages', 'steps', 'physicalEvents', 'sourceEntries',
                        'instructions', 'registrations', 'resizeAttempts'))
                or profile.get('halt') not in (None, 'physical-prefix-stop', 'ExitProcess-nonreturning')):
            raise PrerequisiteError('invalid CRT shard identity')
        # Original provenance contains absolute producer paths. Only its basename
        # selects a shard, and its complete parent must match the frozen location.
        if Path(profile['path']).parent != ROOT / Path(CRT_REFERENCE).parent:
            raise PrerequisiteError('invalid CRT shard path')
        names.add(profile['name'])
        name = str(Path(CRT_REFERENCE).parent / (profile['name'] + '.json.gz'))
        path = Path(root) / name
        if path.is_symlink() or path.resolve().parent != index.parent.resolve():
            raise PrerequisiteError('invalid CRT shard path')
        result[name] = profile['sha256']
    return result


def input_inventory(root, checks):
    if checks == ['static_startup_final']:
        from .static_build_inputs import final_input_inventory
        return final_input_inventory(root)
    root = Path(root)
    paths = set()
    for directory in ('Sources', 'App', 'Tests', 'scripts', 'tools', 'Claw.xcodeproj'):
        for path in (root / directory).rglob('*'):
            if path.is_file() and path.suffix in SUFFIXES and 'GameData' not in path.parts:
                paths.add(str(path.relative_to(root)))
    paths.add('Makefile')
    required = []
    static_inputs = {}
    for static_check in STATIC_CHECKS:
        if static_check in checks:
            static_inputs.update(static_reference_inputs(root, STATIC_CHECKS.index(static_check) + 1))
    if static_inputs:
        required += [EXE, *static_inputs]
    crt_shards = crt_registry_shards(root) if 'crt_registry_source' in checks else {}
    object_shards = application_object_shards(root) if 'application_object_source' in checks else {}
    if 'source_graph' in checks:
        required += [EXE, *GOLDENS]
    if 'tls_manager_source' in checks:
        required += [EXE, MANAGER_REFERENCE]
    if 'tls_values_source' in checks:
        required += [EXE, VALUES_REFERENCE]
    if 'cold_module_source' in checks:
        required += [EXE, MODULE_REFERENCE]
    if 'application_thread_source' in checks:
        required += [EXE, APPLICATION_THREAD_REFERENCE]
    if 'application_object_source' in checks:
        required += [EXE, APPLICATION_OBJECT_REFERENCE, *object_shards]
    if 'crt_registry_source' in checks:
        required += [EXE, CRT_REFERENCE, *crt_shards]
    if 'startup_prefix' in checks:
        required += [EXE, REZ, FEC]
    paths.update(required)
    result = {}
    for name in sorted(paths):
        path = root / name
        if not path.is_file():
            raise PrerequisiteError('missing input: ' + name)
        result[name] = digest(path)
    for name, expected in ((EXE, ORIGINAL_SHA256), (REZ, REZ_SHA256), (FEC, FEC_SHA256),
                           (APPLICATION_OBJECT_REFERENCE, APPLICATION_OBJECT_REFERENCE_SHA256),
                           (CRT_REFERENCE, CRT_REFERENCE_SHA256)):
        if name in result and result[name] != expected:
            raise PrerequisiteError('pinned original fingerprint mismatch: ' + name)
    for name, expected in object_shards.items():
        if result[name] != expected:
            raise PrerequisiteError('application object shard fingerprint mismatch: ' + name)
    for name, expected in static_inputs.items():
        if result[name] != expected:
            raise PrerequisiteError('static frozen input fingerprint mismatch: ' + name)
    for name, expected in crt_shards.items():
        if result[name] != expected:
            raise PrerequisiteError('CRT shard fingerprint mismatch: ' + name)
    result['@git/project-source-membership'] = stable_hash(project_membership(root))
    return result


def toolchain_identity(root=ROOT):
    commands = {'python': [sys.executable, '--version'], 'python3': ['python3', '--version'],
                'clang_path': ['xcrun', '--find', 'clang++'], 'swift_path': ['xcrun', '--find', 'swiftc'],
                'sdk': ['xcrun', '--show-sdk-path'], 'sdk_version': ['xcrun', '--show-sdk-version']}
    python3 = shutil.which('python3')
    if python3 is None:
        raise PrerequisiteError('python3 not available')
    commands['python3'] = [python3, '--version']
    result = {'python_executable': str(Path(sys.executable).resolve()),
              'python3_executable': str(Path(python3).resolve())}
    research_python = Path(root) / 'work/test-env/bin/python'
    if research_python.exists():
        commands['research_python'] = [str(research_python), '--version']
        commands['unicorn'] = [str(research_python), '-c',
                              'import json,pathlib,unicorn; print(json.dumps({"package_version":unicorn.__version__,"core_version":unicorn.uc_version(),"module_path":str(pathlib.Path(unicorn.__file__).resolve())},sort_keys=True))']
        result['research_python_executable'] = str(research_python.resolve())
    for name, command in commands.items():
        result[name] = subprocess.check_output(command, cwd=root, text=True, stderr=subprocess.STDOUT, timeout=20).strip()
    for name in ('clang', 'swift'):
        result[name] = subprocess.check_output([result[name + '_path'], '--version'], text=True, timeout=20).strip()
    return result


def fingerprint(checks, inputs, toolchain):
    return stable_hash({'schema': SCHEMA, 'checks': select_checks(checks), 'inputs': inputs,
                        'toolchain': toolchain, 'mode': 'asan-ubsan-unoptimized-jobs1'})


def validate_certificate(check_id, payload):
    def require(condition, message):
        if not condition:
            raise ValueError('invalid ' + check_id + ' certificate: ' + message)
    require(isinstance(payload, dict) and payload.get('status') == 'pass', 'status')
    if check_id == 'project':
        require(payload.get('command') == 'project-check' and payload.get('in_sync') is True, 'project identity')
        for key in ('compiled_cpp', 'compiled_swift', 'bridged_headers'):
            require(type(payload.get(key)) is int and payload[key] > 0, key)
    elif check_id == 'source_graph':
        require(payload.get('mode') == 'sanitized' and payload.get('sanitized') is True
                and payload.get('optimized') is False, 'mode')
        replay, edges = payload.get('replay', {}), payload.get('edge_validation', {})
        require(isinstance(replay, dict) and replay.get('status') == 'pass'
                and replay.get('profiles') == 448 and replay.get('unique_reference_profiles') == 288, 'replay')
        require(isinstance(edges, dict) and edges.get('status') == 'pass' and edges.get('edges') == 9, 'edges')
        require(isinstance(payload.get('reference_sha256'), dict) and set(payload['reference_sha256']) == set(GOLDENS), 'references')
        require(all(isinstance(v, str) and re.fullmatch('[0-9a-f]{64}', v) for v in payload['reference_sha256'].values()), 'reference digests')
        require(isinstance(payload.get('cache_key'), str) and len(payload['cache_key']) == 64, 'build identity')
    elif check_id == 'tls_manager_source':
        require(type(payload.get('schema')) is int and payload['schema'] == 1
                and payload.get('command') == 'native-mfc-tls-manager-source', 'identity')
        require(payload.get('sanitized') is True and payload.get('optimized') is False, 'mode')
        replay = payload.get('replay')
        require(isinstance(replay, dict) and replay.get('status') == 'pass', 'replay')
        for key, count in (('profiles', 9), ('roots', 119), ('physical_events', 271), ('child_entries', 13)):
            require(type(replay.get(key)) is int and replay[key] == count, key)
        require(type(replay.get('native_controls')) is int and replay['native_controls'] >= 65, 'native controls')
        require(type(replay.get('assertions')) is int and replay['assertions'] >= 6182, 'assertions')
        require(isinstance(payload.get('reference_sha256'), str)
                and re.fullmatch('[0-9a-f]{64}', payload['reference_sha256']), 'reference digest')
        require(isinstance(payload.get('cache_key'), str)
                and re.fullmatch('[0-9a-f]{64}', payload['cache_key']), 'build identity')
    elif check_id == 'tls_values_source':
        require(type(payload.get('schema')) is int and payload['schema'] == 1
                and payload.get('command') == 'native-mfc-tls-values-source', 'identity')
        require(payload.get('sanitized') is True and payload.get('optimized') is False, 'mode')
        replay = payload.get('replay')
        require(isinstance(replay, dict) and replay.get('status') == 'pass', 'replay')
        for key, count in (('profiles', 11), ('roots', 55), ('physical_events', 399),
                           ('observed_entries', 366), ('reference_entries', 410),
                           ('reference_only_entries', 44)):
            require(type(replay.get(key)) is int and replay[key] == count, key)
        require(type(replay.get('native_controls')) is int and replay['native_controls'] >= 144, 'native controls')
        require(type(replay.get('assertions')) is int and replay['assertions'] >= 29371, 'assertions')
        sites = replay.get('unobserved_sites')
        require(isinstance(sites, list) and len(sites) == 44, 'reference-only sites')
        for site in sites:
            require(isinstance(site, dict) and site.get('function') == 0x503167
                    and site.get('return_pc') == 0x5033ce, 'reference-only identity')
            require(isinstance(site.get('profile'), str) and bool(site['profile'])
                    and type(site.get('root_step')) is int and site['root_step'] >= 0
                    and type(site.get('frame')) is int and 0x01ff0000 <= site['frame'] < 0x02010000
                    and site['frame'] % 4 == 0, 'reference-only frame')
        require(len({(s['profile'], s['root_step'], s['frame']) for s in sites}) == 44, 'duplicate reference-only site')
        for key in ('reference_sha256', 'cache_key'):
            require(isinstance(payload.get(key), str) and re.fullmatch('[0-9a-f]{64}', payload[key]), key)
    elif check_id == 'cold_module_source':
        require(type(payload.get('schema')) is int and payload['schema'] == 1
                and payload.get('command') == 'native-mfc-cold-module', 'identity')
        require(payload.get('sanitized') is True and payload.get('optimized') is False, 'mode')
        require(payload.get('reference_sha256') == MODULE_REFERENCE_SHA256, 'frozen reference')
        require(isinstance(payload.get('cache_key'), str)
                and re.fullmatch('[0-9a-f]{64}', payload['cache_key']), 'build identity')
        replay = payload.get('replay')
        require(isinstance(replay, dict) and replay.get('status') == 'pass', 'replay')
        for key, count in (('profiles', 29), ('roots', 30), ('physical_events', 336),
                           ('observed_entries', 311), ('reference_entries', 339),
                           ('reference_only_entries', 28)):
            require(type(replay.get(key)) is int and replay[key] == count, key)
        require(type(replay.get('native_controls')) is int and replay['native_controls'] >= 83, 'native controls')
        require(type(replay.get('original_assertions')) is int and replay['original_assertions'] >= 71668, 'original assertions')
        require(type(replay.get('assertions')) is int
                and replay['assertions'] == replay['original_assertions'] + replay['native_controls'], 'assertion accounting')
        require(replay.get('catch_executed') is False
                and replay.get('application_getter_executed') is False, 'bounded execution scope')
        sites = replay.get('unobserved_sites')
        require(isinstance(sites, list) and len(sites) == 28, 'reference-only sites')
        identities = []
        for site in sites:
            require(isinstance(site, dict), 'reference-only object')
            pair = (site.get('function'), site.get('return_pc'))
            require(pair in ((0x503167, 0x5033ce), (0x502e47, 0x502ea8)), 'reference-only identity')
            require(isinstance(site.get('profile'), str) and bool(site['profile'])
                    and type(site.get('root_step')) is int and site['root_step'] >= 0
                    and type(site.get('frame')) is int and 0x01ff0000 <= site['frame'] < 0x02010000
                    and site['frame'] % 4 == 0, 'reference-only frame')
            identities.append((site['profile'], site['root_step'], site['function'], site['frame']))
        require(len(set(identities)) == 28, 'duplicate reference-only site')
        require(sum(s['function'] == 0x503167 for s in sites) == 18, 'owned setter count')
    elif check_id == 'application_thread_source':
        require(type(payload.get('schema')) is int and payload['schema'] == 1
                and payload.get('command') == 'native-mfc-application-thread-source', 'identity')
        require(payload.get('sanitized') is True and payload.get('optimized') is False, 'mode')
        require(payload.get('reference_sha256') == APPLICATION_THREAD_REFERENCE_SHA256, 'frozen reference')
        require(isinstance(payload.get('cache_key'), str)
                and re.fullmatch('[0-9a-f]{64}', payload['cache_key']), 'build identity')
        replay = payload.get('replay')
        require(isinstance(replay, dict) and replay.get('status') == 'pass', 'replay')
        for key, count in (('profiles', 10), ('roots', 22), ('physical_events', 267),
                           ('observed_entries', 255), ('reference_entries', 300),
                           ('reference_only_entries', 45), ('bridges', 11)):
            require(type(replay.get(key)) is int and replay[key] == count, key)
        require(type(replay.get('native_controls')) is int and replay['native_controls'] >= 166, 'native controls')
        require(type(replay.get('original_assertions')) is int and replay['original_assertions'] >= 68954, 'original assertions')
        require(type(replay.get('assertions')) is int
                and replay['assertions'] == replay['original_assertions'] + replay['native_controls'], 'assertion accounting')
        require(replay.get('catch_executed') is False
                and replay.get('application_getter_executed') is True
                and replay.get('whole_cwinapp_executed') is False, 'bounded execution scope')
        sites = replay.get('unobserved_sites')
        require(isinstance(sites, list) and len(sites) == 45, 'reference-only sites')
        expected_sites = {(0x503167, 0x5033ce): 15, (0x502e47, 0x502ea8): 10,
                          (0x50210b, 0x502329): 5, (0x4f5e89, 0x502137): 5,
                          (0x4f5e89, 0x502145): 5, (0x4f5133, 0x502153): 5}
        identities = []
        for site in sites:
            require(isinstance(site, dict), 'reference-only object')
            pair = (site.get('function'), site.get('return_pc'))
            require(pair in expected_sites, 'reference-only identity')
            require(isinstance(site.get('profile'), str) and bool(site['profile'])
                    and type(site.get('root_step')) is int and site['root_step'] >= 0
                    and type(site.get('frame')) is int and 0x01ff0000 <= site['frame'] < 0x02010000
                    and site['frame'] % 4 == 0, 'reference-only frame')
            identities.append((site['profile'], site['root_step'], site['function'], site['return_pc'], site['frame']))
        require(len(set(identities)) == 45, 'duplicate reference-only site')
        for pair, count in expected_sites.items():
            require(sum((s['function'], s['return_pc']) == pair for s in sites) == count, 'owned internal count')
    elif check_id == 'application_object_source':
        require(type(payload.get('schema')) is int and payload['schema'] == 1
                and payload.get('command') == 'native-mfc-application-object', 'identity')
        require(payload.get('sanitized') is True and payload.get('optimized') is False, 'mode')
        require(payload.get('complete_reference') is True, 'complete frozen reference')
        require(payload.get('reference_sha256') == APPLICATION_OBJECT_REFERENCE_SHA256, 'frozen reference')
        require(isinstance(payload.get('cache_key'), str)
                and re.fullmatch('[0-9a-f]{64}', payload['cache_key']), 'build identity')
        replay = payload.get('replay')
        require(isinstance(replay, dict) and replay.get('status') == 'pass', 'replay')
        counts = dict(profiles=61, roots=62, returned_roots=21, stopped_roots=41,
                      physical_events=1358, reference_physical_events=1366,
                      observed_entries=1356, reference_only_entries=316,
                      native_unobserved_entries=26, reference_entries=1698,
                      missing_native_prefixes=8, later_original_physical_events=8,
                      later_original_entries=0)
        for key, count in counts.items():
            require(type(replay.get(key)) is int and replay[key] == count, key)
        require(type(replay.get('native_controls')) is int and replay['native_controls'] >= 165, 'native controls')
        require(type(replay.get('original_assertions')) is int and replay['original_assertions'] >= 571962, 'original assertions')
        require(type(replay.get('assertions')) is int
                and replay['assertions'] == replay['original_assertions'] + replay['native_controls'], 'assertion accounting')
        require(replay.get('whole_cwinapp_executed') is True
                and replay.get('catch_executed') is False, 'bounded execution scope')
        sites = replay.get('unobserved_sites')
        require(isinstance(sites, list) and len(sites) == 342, 'unobserved sites')
        expected_sites = {(0x4f6a9a, 0x503526, True): 62, (0x50354d, 0x50353e, True): 62,
                          (0x503167, 0x5033ce, True): 74, (0x502e47, 0x502ea8, True): 40,
                          (0x4f5e89, 0x502137, True): 26, (0x4f5e89, 0x502145, True): 26,
                          (0x4f5133, 0x502153, True): 26, (0x50210b, 0x502329, False): 26}
        identities = []
        for site in sites:
            require(isinstance(site, dict), 'unobserved object')
            triple = (site.get('function'), site.get('return_pc'), site.get('original_defined'))
            require(type(site.get('function')) is int and type(site.get('return_pc')) is int
                    and type(site.get('original_defined')) is bool and triple in expected_sites, 'unobserved identity')
            require(isinstance(site.get('profile'), str) and bool(site['profile'])
                    and type(site.get('root_step')) is int and 0 <= site['root_step'] <= 1
                    and type(site.get('frame')) is int and 0x01ff0000 <= site['frame'] < 0x02010000
                    and site['frame'] % 4 == 0, 'unobserved frame')
            if not site['original_defined']:
                require(isinstance(site.get('reason'), str) and bool(site['reason'].strip()), 'unobserved owned reason')
            identities.append((site['profile'], site['root_step'], site['function'], site['return_pc'], site['frame']))
        require(len(set(identities)) == 342, 'duplicate unobserved site')
        for triple, count in expected_sites.items():
            require(sum((x['function'], x['return_pc'], x['original_defined']) == triple for x in sites) == count,
                    'unobserved count')
        missing = replay.get('missing_native_sites')
        require(isinstance(missing, list) and len(missing) == 8, 'missing native sites')
        expected_missing = {
            'allocation-null-at-2': (0x5030af, 0x2007eac),
            'allocation-null-at-3': (0x502f9c, 0x2007ea4),
            'allocation-null-at-4': (0x502f9c, 0x2007ea8),
            'allocation-null-at-5': (0x503205, 0x2007eb4),
            'allocation-null-at-6': (0x502f9c, 0x2007e80),
            'allocation-null-at-7': (0x502f9c, 0x2007ea8),
            'allocation-null-at-8': (0x503205, 0x2007eb8),
            'tls-index-exhausted-original-failure': (0x502fea, 0x2007ec0)}
        require(all(isinstance(x, dict) and isinstance(x.get('profile'), str)
                    and all(type(x.get(k)) is int for k in ('function', 'return_pc', 'frame'))
                    and x['function'] == 0x4f50fd
                    and type(x.get('root_step')) is int and x['root_step'] == 0
                    and x.get('profile') in expected_missing
                    and (x.get('return_pc'), x.get('frame')) == expected_missing[x['profile']]
                    for x in missing), 'missing native identity')
        require({x['profile'] for x in missing} == set(expected_missing), 'missing native profiles')
    elif check_id in STATIC_CHECKS:
        validate_static_certificate(payload, STATIC_CHECKS.index(check_id) + 1)
    elif check_id == 'crt_registry_source':
        require(type(payload.get('schema')) is int and payload['schema'] == 1
                and payload.get('command') == 'native-crt-exit-registry', 'identity')
        require(payload.get('whole_leaves') is True and payload.get('sanitized') is True
                and payload.get('optimized') is False, 'whole sanitized mode')
        require(payload.get('scope') == 'prepared original leaf roots at4a5896; admitted leaf CALLs execute natively; no constructor wrappers', 'bounded CRT scope')
        require(payload.get('reference_provenance_sha256') == CRT_REFERENCE_SHA256, 'frozen provenance')
        for field in ('cache_key', 'certificate_sha256'):
            require(isinstance(payload.get(field), str) and re.fullmatch('[0-9a-f]{64}', payload[field]), field)
        for field in ('certificate', 'report_path'):
            require(isinstance(payload.get(field), str) and Path(payload[field]).is_absolute()
                    and '..' not in Path(payload[field]).parts, field)
        profiles = payload.get('profiles')
        require(isinstance(profiles, list) and len(profiles) == 21, 'profiles')
        require(all(isinstance(p, dict) and isinstance(p.get('profile'), str) for p in profiles), 'profile objects')
        require({p['profile'] for p in profiles} == set(CRT_PROFILES), 'profile identities')
        for profile in profiles:
            name = profile['profile']
            reference_hash, expected_counts, original_assertions, outcomes_hash = CRT_PROFILES[name]
            require(profile.get('status') == 'pass' and profile.get('command') == 'native-crt-exit-registry'
                    and profile.get('scope') == 'prepared-original-leaf-roots', 'profile scope')
            require(profile.get('reference_sha256') == reference_hash, 'profile reference digest')
            for field, count in zip(CRT_COUNT_FIELDS, expected_counts):
                require(type(profile.get(field)) is int and profile[field] == count, name + ' ' + field)
            controls = profile.get('native_controls')
            require(type(controls) is int and controls >= (40 if name == 'inplace126' else 0), 'native controls')
            require(type(profile.get('assertions')) is int
                    and profile['assertions'] >= original_assertions + controls, 'original assertions')
            require(profile['reference_only_entries'] == profile['reference_only_internal_entries']
                    + profile['reference_entries_after_native_stop'], 'unobserved accounting')
            require(isinstance(profile.get('native_snapshot_sha256'), str)
                    and re.fullmatch('[0-9a-f]{64}', profile['native_snapshot_sha256']), 'snapshot digest')
            require(isinstance(profile.get('native_snapshot'), str)
                    and Path(profile['native_snapshot']).is_absolute()
                    and Path(profile['native_snapshot']).name == name + '-native.json'
                    and '..' not in Path(profile['native_snapshot']).parts, 'snapshot identity')
            outcomes = profile.get('root_outcomes')
            require(isinstance(outcomes, list) and len(outcomes) == profile['roots'], 'root outcomes')
            for index, outcome in enumerate(outcomes):
                require(isinstance(outcome, dict) and type(outcome.get('step')) is int
                        and outcome['step'] == index and type(outcome.get('leaf')) is bool
                        and type(outcome.get('completed')) is bool, 'root outcome types')
                for field in ('function', 'returnPC', 'frame', 'referenceState'):
                    require(type(outcome.get(field)) is int and 0 <= outcome[field] <= 0xffffffff, 'root ' + field)
                require(isinstance(outcome.get('arguments'), list)
                        and all(type(x) is int and 0 <= x <= 0xffffffff for x in outcome['arguments']), 'root arguments')
                require(outcome.get('eax') is None or (type(outcome['eax']) is int
                        and 0 <= outcome['eax'] <= 0xffffffff), 'root EAX')
                cpu = outcome.get('outputCPU')
                require(isinstance(cpu, dict) and set(cpu) == {'eax', 'ebp', 'ebx', 'ecx', 'edi', 'edx', 'eflags', 'eip', 'esi', 'esp', 'fsHead'}
                        and all(type(x) is int and 0 <= x <= 0xffffffff for x in cpu.values()), 'root CPU')
                if outcome['completed']:
                    require('stop' not in outcome and type(outcome.get('eax')) is int, 'returned outcome')
                else:
                    stop = outcome.get('stop')
                    require(isinstance(stop, dict) and isinstance(stop.get('diagnostic'), str)
                            and bool(stop['diagnostic']) and all(type(stop.get(k)) is int
                            and 0 <= stop[k] <= 0xffffffff for k in ('address', 'code')), 'stopped outcome')
            require(sum(o['leaf'] for o in outcomes) == profile['leaf_roots'], 'actual leaf executions')
            require(stable_hash(outcomes) == outcomes_hash, 'exact original root outcomes')
        negatives = payload.get('negative_leaf_controls')
        kinds = {'callback', 'parentPC', 'argumentStore', 'returnStore', 'frame', 'bodyEAX', 'cleanupECX', 'cleanupFlags'}
        require(isinstance(negatives, list) and len(negatives) == 8
                and all(isinstance(n, dict) and isinstance(n.get('negative_leaf'), str)
                        and n.get('status') == 'pass' and type(n.get('assertions')) is int
                        and n['assertions'] >= 2110 for n in negatives), 'negative leaf controls')
        require({n['negative_leaf'] for n in negatives} == kinds, 'negative leaf identities')
    elif check_id == 'startup_prefix':
        require(payload.get('schema') == 1 and payload.get('command') == 'native-application-pregraphics'
                and payload.get('scope') == 'startup-prefix', 'identity')
        profiles = payload.get('profiles')
        require(isinstance(profiles, list) and len(profiles) == 6, 'profiles')
        require(all(isinstance(p, dict) for p in profiles), 'profile object')
        require({p.get('name') for p in profiles} == {'empty', 'options', 'user', 'empty-user', 'bytes', 'boundaries'}, 'profile names')
        for profile in profiles:
            stop = profile.get('stop', {})
            require(profile.get('completed') is False and isinstance(stop, dict)
                    and stop.get('diagnostic') == 'missingDependency', 'bounded stop')
            for key in ('address', 'code'):
                value = stop.get(key)
                try:
                    value = int(value, 16) if isinstance(value, str) and value.startswith('0x') else value
                    require(type(value) is int and 0 < value <= 0xffffffff, 'stop ' + key)
                except (TypeError, ValueError):
                    raise ValueError('invalid startup stop ' + key)
            for key in ('callbacks', 'registry_callbacks'):
                require(type(profile.get(key)) is int and profile[key] > 0, key)
        require(payload.get('source_callbacks') == sum(p['callbacks'] for p in profiles), 'callback total')
        require(payload.get('registry_callbacks') == sum(p['registry_callbacks'] for p in profiles), 'registry total')
        require(isinstance(payload.get('reference_sha256'), str) and re.fullmatch('[0-9a-f]{64}', payload['reference_sha256']), 'reference digest')
        require(isinstance(payload.get('limits'), list) and bool(payload['limits']), 'limits')
    else:
        raise ValueError('unknown check: ' + check_id)


def read_certificate(check_id, stdout_path):
    lines = Path(stdout_path).read_text().splitlines()
    if not lines:
        raise ValueError('missing structured final stdout')
    value = json.loads(lines[-1])
    validate_certificate(check_id, value)
    return value


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def artifacts_valid(check, attempt_dir, require_verified=True):
    try:
        if not isinstance(check, dict) or not isinstance(check.get('artifacts'), dict):
            return False
        if check.get('id') not in CHECKS or (require_verified and (check.get('status') != 'verified' or check.get('exit_code') != 0)):
            return False
        directory = Path(attempt_dir) / check['id']
        if directory.is_symlink() or directory.resolve().parent != Path(attempt_dir).resolve():
            return False
        for name in ('stdout', 'stderr', 'result'):
            artifact = directory / (name + ('.json' if name == 'result' else '.log'))
            if artifact.is_symlink() or digest(artifact) != check['artifacts'][name]:
                return False
        if check.get('status') != 'verified':
            return json.loads((directory / 'result.json').read_text()) == check.get('certificate')
        certificate = read_certificate(check['id'], directory / 'stdout.log')
        if check['id'] == 'startup_prefix':
            reference = directory / 'reference.json'
            if reference.is_symlink() or digest(reference) != certificate['reference_sha256']:
                return False
        if check['id'] in STATIC_CHECKS:
            if static_evidence(certificate, directory, Path(attempt_dir).parents[2]) != check.get('evidence'):
                return False
        if check['id'] == 'crt_registry_source':
            if crt_evidence(certificate, directory, Path(attempt_dir).parents[2]) != check.get('evidence'):
                return False
        return certificate == json.loads((directory / 'result.json').read_text()) == check['certificate']
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return False


STATIC_PUBLISH = """
import json, os, subprocess
reports=[]
for asan,opt in [('1','0'),('0','1')]:
 env=dict(os.environ,CLAW_NATIVE_ASAN=asan,CLAW_NATIVE_OPTIMIZE=opt)
 done=subprocess.run(['scripts/check-native-static-startup.sh'],env=env,capture_output=True,text=True)
 if done.returncode:
  print(done.stdout);print(done.stderr);raise SystemExit(done.returncode)
 reports.append(json.loads(done.stdout.splitlines()[-1]))
print(json.dumps(dict(status='pass',command='static-startup-prefix',modes=reports)))
"""


STATIC_THREE_PUBLISH = STATIC_PUBLISH.replace("['scripts/check-native-static-startup.sh']", "['scripts/check-native-static-startup.sh', '--v2']").replace('static-startup-prefix', 'static-startup-three')

STATIC_SEVEN_PUBLISH = STATIC_PUBLISH.replace("['scripts/check-native-static-startup.sh']", "['scripts/check-native-static-startup.sh', '--v3']").replace('static-startup-prefix', 'static-startup-seven')

STATIC_FIFTEEN_PUBLISH = STATIC_PUBLISH.replace("['scripts/check-native-static-startup.sh']", "['scripts/check-native-static-startup.sh', '--v4']").replace('static-startup-prefix', 'static-startup-fifteen')

STATIC_THIRTYFOUR_PUBLISH = STATIC_PUBLISH.replace("['scripts/check-native-static-startup.sh']", "['scripts/check-native-static-startup.sh', '--v5']").replace('static-startup-prefix', 'static-startup-thirtyfour')


STATIC_APPLICATION_PUBLISH = STATIC_PUBLISH.replace("['scripts/check-native-static-startup.sh']", "['scripts/check-native-static-startup.sh', '--v6']").replace('static-startup-prefix', 'static-startup-application')


STATIC_FINAL_PUBLISH = STATIC_PUBLISH.replace("['scripts/check-native-static-startup.sh']", "['scripts/check-native-static-startup.sh', '--v9']").replace('static-startup-prefix', 'static-startup-final')

STATIC_LIST_PUBLISH = STATIC_PUBLISH.replace("['scripts/check-native-static-startup.sh']", "['scripts/check-native-static-startup.sh', '--v8']").replace('static-startup-prefix', 'static-startup-list')

STATIC_EXTENDED_PUBLISH = STATIC_PUBLISH.replace("['scripts/check-native-static-startup.sh']", "['scripts/check-native-static-startup.sh', '--v7']").replace('static-startup-prefix', 'static-startup-extended')


STATIC_EXTENDED_ARCHIVE_ROOT = 'work/coordination/source-fixture-original-producer-inputs'
STATIC_EXTENDED_ARCHIVE_MANIFEST = STATIC_EXTENDED_ARCHIVE_ROOT + '/manifest.json'
STATIC_EXTENDED_ARCHIVE_SHA256 = 'b26bc65cb0264da04d3d45533d2ab2b89356f530b92e88ebda582d8303a216da'
STATIC_EXTENDED_ARCHIVED_PRODUCERS = {
    'Tests/clawparity/kernel.py':'85c31b38083e0377800acb41b16f90286e668c3ae1656d7d7d88330a8c70686b',
    'Tests/clawparity/env.py':'c824ec411b823afc2f7a77365d1db8233878b7c543b0aef1422f9e3a71d1b087',
}


def static_extended_archived_producers(producers, archive_root):
    """Exactly two archived original inputs; current native inputs stay separate."""
    archive_root=Path(archive_root).resolve();result=dict(producers)
    archived={STATIC_EXTENDED_ARCHIVE_MANIFEST:STATIC_EXTENDED_ARCHIVE_SHA256}
    for name,expected in STATIC_EXTENDED_ARCHIVED_PRODUCERS.items():
        if result.pop(name,None)!=expected:
            raise PrerequisiteError('static archived producer is not the named original input')
        archived[STATIC_EXTENDED_ARCHIVE_ROOT+'/'+name]=expected
    for name,expected in archived.items():
        path=Path(name)
        if (path.is_absolute() or '..' in path.parts
                or any((archive_root/Path(*path.parts[:i+1])).is_symlink() for i in range(len(path.parts)))
                or not (archive_root/path).is_file() or (archive_root/path).resolve()!=(archive_root/path).absolute()
                or digest(archive_root/path)!=expected):
            raise PrerequisiteError('static archived original producer fingerprint/path: '+name)
    manifest=json.loads((archive_root/STATIC_EXTENDED_ARCHIVE_MANIFEST).read_text())
    expected_rows=[dict(source_path=name,archive_path=STATIC_EXTENDED_ARCHIVE_ROOT+'/'+name,
        sha256=expected,bytes=(archive_root/STATIC_EXTENDED_ARCHIVE_ROOT/name).stat().st_size)
        for name,expected in STATIC_EXTENDED_ARCHIVED_PRODUCERS.items()]
    current=manifest.get('current_inputs')
    if (type(manifest.get('schema_version')) is not int or manifest['schema_version']!=1
            or manifest.get('archived_inputs')!=expected_rows
            or not isinstance(current,list) or len(current)!=2
            or {row.get('path') for row in current if isinstance(row,dict)}!=set(STATIC_EXTENDED_ARCHIVED_PRODUCERS)
            or any(not isinstance(row,dict) or set(row)!={'path','sha256','bytes'}
                or not isinstance(row['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',row['sha256'])
                or type(row['bytes']) is not int or row['bytes']<=0 for row in current)):
        raise PrerequisiteError('static archived original manifest mapping')
    result.update(archived)
    return result


STATIC_LIST_REFERENCE = 'work/native-static-startup-check/frozen-v8/provenance.json'
STATIC_LIST_REFERENCE_SHA256 = '61d4840bbfe6805f2be0c790fac951d7a364f13920951810e64e3db0a067a603'
STATIC_LIST_SUPPLEMENTAL = 'work/native-static-startup-check/frozen-v8/supplemental-input-inventory.json'
STATIC_LIST_SUPPLEMENTAL_SHA256 = 'f5a4f8ffbeebd79a1c1086df06e13571933672637d49bac17ce50970d8b1f34c'


def static_list_archived_producers(provenance, archive_root):
    """Resolve v8's complete capture-time archive, never a live drift fallback."""
    archive_root=Path(archive_root)
    base=Path(STATIC_LIST_REFERENCE).parent
    def checked(path, expected):
        if (not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected)
                or path.is_absolute() or '..' in path.parts
                or any((archive_root/Path(*path.parts[:i+1])).is_symlink() for i in range(len(path.parts)))
                or not (archive_root/path).is_file() or digest(archive_root/path)!=expected):
            raise PrerequisiteError('static list archived input drift or path')
    checked(Path(STATIC_LIST_SUPPLEMENTAL),STATIC_LIST_SUPPLEMENTAL_SHA256)
    supplemental=json.loads((archive_root/STATIC_LIST_SUPPLEMENTAL).read_text())
    inventory=provenance.get('frozenInputInventory')
    producers=provenance.get('producerHashes')
    if (not isinstance(inventory,dict) or not isinstance(producers,dict) or len(inventory)!=74
            or set(inventory)!=set(producers) or not isinstance(supplemental,dict) or len(supplemental)!=10
            or set(inventory)&set(supplemental) or provenance.get('liveInputsChangedAfterLoad')!=[]):
        raise PrerequisiteError('static list archived inventory')
    result={STATIC_LIST_SUPPLEMENTAL:STATIC_LIST_SUPPLEMENTAL_SHA256}
    for name,row in {**inventory,**supplemental}.items():
        source=Path(name)
        if (source.is_absolute() or '..' in source.parts or not source.parts or source.as_posix()!=name
                or not isinstance(row,dict) or set(row)!={'path','sha256'}
                or row['path']!='inputs/'+name or (name in producers and row['sha256']!=producers[name])):
            raise PrerequisiteError('static list archived mapping')
        path=base/row['path']; checked(path,row['sha256']); result[path.as_posix()]=row['sha256']
    return result


STATIC_FINAL_REFERENCE = 'work/native-static-startup-check/frozen-v9/provenance.json'
STATIC_FINAL_REFERENCE_SHA256 = 'f159f3091855fb84a194a4f77cd9508b0f38c7b6611ebefdca66989aed1e44b3'
STATIC_FINAL_POLICY_SHA256 = '6aefbfa66b7bdb8429503d33b28cd13f9195e52ce36ba153e0d94901b5326b41'
STATIC_FINAL_ARCHIVES = {'input-archive.json':'eee62116115f60db536c433ab284467995069d52f1ad84894677e380634b31dd',
    'supplemental-input-archive.json':'b9671f776138b9be683d4bdb7474f691683d31dcb4a14603a8850c73b79bcf6e'}

STATIC_FINAL_METADATA = {
    'provenance-metadata-addendum-v1.json':'a5d6812a3d843d9fa1f4fe71d7e728d0abfdf94a4d96b1a396c239018890cef0',
    'metadata-policy-v1.json':'76b0dedbda03619f66bf0b0525aa23328e9913a298ec3234fdd4ee86b12cebfe',
    'metadata_guard_v1.py':'f6c447b08d05102e7084ea78286e583e4aee2431030bd2981911144f9bd78eae',
    'metadata-validation-v1.json':'eb8b91e13e7e495ab09289dcf37de916d7775426d699573fe8d95ab3e71ddbab',
    'independent-verification.json':'913438380d1a45b65b31fe509b03349b768f7d1f38d4a927075080148e875dd1'}


def static_final_archived_producers(provenance, archive_root):
    """Require both immutable capture capsules, including the verifier erratum."""
    archive_root=Path(archive_root);base=Path(STATIC_FINAL_REFERENCE).parent;result={}
    def checked(relative, expected, size=None):
        path=Path(relative)
        if (not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected)
                or path.is_absolute() or '..' in path.parts or path.as_posix()!=str(relative)
                or any((archive_root/Path(*path.parts[:i+1])).is_symlink() for i in range(len(path.parts)))
                or not (archive_root/path).is_file() or digest(archive_root/path)!=expected
                or size is not None and (type(size) is not int or size<0 or (archive_root/path).stat().st_size!=size)):
            raise PrerequisiteError('static final archived input fingerprint/path/size')
        result[path.as_posix()]=expected
    if provenance.get('policySha256')!=STATIC_FINAL_POLICY_SHA256 or provenance.get('liveInputsChangedAfterLoad')!=[]:
        raise PrerequisiteError('static final frozen policy identity')
    for filename,field,prefix,count,status,hashfield in (
            ('input-archive.json','frozenInputInventory','inputs/',93,'archived-before-any-capture','inputArchiveSha256'),
            ('supplemental-input-archive.json','supplementalInputInventory','inputs-supplemental/',3,'archived-before-remaining25-captures','supplementalArchiveSha256')):
        expected=STATIC_FINAL_ARCHIVES[filename];checked(base/filename,expected)
        capsule=json.loads((archive_root/base/filename).read_text());inventory=provenance.get(field)
        if (provenance.get(hashfield)!=expected or not isinstance(inventory,dict) or len(inventory)!=count
                or capsule.get('inputInventory')!=inventory or capsule.get('status')!=status
                or capsule.get('policySha256')!=STATIC_FINAL_POLICY_SHA256):
            raise PrerequisiteError('static final archive inventory identity')
        if filename=='supplemental-input-archive.json' and capsule.get('initialArchiveSha256')!=STATIC_FINAL_ARCHIVES['input-archive.json']:
            raise PrerequisiteError('static final supplemental predecessor')
        for name,row in inventory.items():
            source=Path(name)
            if (source.is_absolute() or '..' in source.parts or source.as_posix()!=name
                    or not isinstance(row,dict) or set(row)!={'path','sha256','bytes'} or row['path']!=prefix+name):
                raise PrerequisiteError('static final archived mapping')
            checked(base/row['path'],row['sha256'],row['bytes'])
    erratum_name=str(base/'verifier-receipt-erratum.json')
    expected_erratum=provenance.get('verifierErratum');row=provenance['supplementalInputInventory'].get(erratum_name)
    if (not isinstance(expected_erratum,dict) or not row or json.loads((archive_root/base/row['path']).read_text())!=expected_erratum
            or expected_erratum.get('policyChanged') is not False or expected_erratum.get('regeneratedOriginalExecution') is not False):
        raise PrerequisiteError('static final verifier erratum identity')
    controls=provenance.get('controls')
    if not isinstance(controls,list) or [row.get('name') for row in controls]!=['fresh119-continuity','fresh133-continuity']:
        raise PrerequisiteError('static final continuity inventory')
    for row in controls:
        if row.get('path')!=row['name']+'.json.gz':raise PrerequisiteError('static final continuity path')
        checked(base/row['path'],row['sha256'],row['bytes'])
    # Post-capture reader-contract evidence is retained separately from producer inputs.
    for filename,expected in STATIC_FINAL_METADATA.items():checked(base/filename,expected)
    addendum=json.loads((archive_root/base/'provenance-metadata-addendum-v1.json').read_text())
    link=lambda name:dict(path=str(base/name),sha256=STATIC_FINAL_METADATA[name])
    if (addendum.get('schema')!='claw-v9-provenance-metadata-addendum-v1'
            or addendum.get('status')!='PASS-authoritative-metadata-validated'
            or addendum.get('capturedProvenance')!=dict(path=STATIC_FINAL_REFERENCE,sha256=STATIC_FINAL_REFERENCE_SHA256)
            or addendum.get('independentExecutionVerification')!=link('independent-verification.json')
            or addendum.get('metadataFiles')!={name:link(name)for name in ('metadata-policy-v1.json','metadata_guard_v1.py','metadata-validation-v1.json')}
            or any(addendum.get(key)is not False for key in ('capturedOutputsChanged','originalExecutionRepeated','policyChanged'))):
        raise PrerequisiteError('static final metadata addendum links')
    validation=json.loads((archive_root/base/'metadata-validation-v1.json').read_text())
    plan_path=provenance['frozenInputInventory']['work/coordination/static-final-original-reference-plan.json']['path']
    plan=json.loads((archive_root/base/plan_path).read_text())
    declared={row['name']:row['inputs']for row in plan['profiles']+plan['continuityControls']}
    rows=validation.get('profiles')
    keys=('version','processVersion','scalarPolicy','dcPolicy','releasePolicy','borrowedPolicy','messagePolicy','messageInitial','capsPolicy','physicalStop')
    expected_rows=[dict(name=row['name'],platformProfileInputs={key:declared[row['name']].get(key)for key in keys})for row in provenance['controls']+provenance['profiles']]
    if (validation.get('status')!='PASS' or validation.get('profilesChecked')!=28
            or validation.get('legacySelectorRejections')!=84 or rows!=expected_rows
            or validation.get('capturedProvenanceSha256')!=STATIC_FINAL_REFERENCE_SHA256
            or validation.get('metadataPolicySha256')!=STATIC_FINAL_METADATA['metadata-policy-v1.json']
            or validation.get('guardSha256')!=STATIC_FINAL_METADATA['metadata_guard_v1.py']
            or validation.get('originalExecutionRepeated')is not False or validation.get('capturedOutputsChanged')is not False):
        raise PrerequisiteError('static final metadata selector validation')
    return result


def static_producer_hashes(provenance, root, version, archive_root=None):
    """Normalize historical paths or resolve v8 capture-time archived inputs."""
    if version==9:
        return static_final_archived_producers(provenance,archive_root if archive_root is not None else root)
    if version==8:
        return static_list_archived_producers(provenance,archive_root if archive_root is not None else root)
    if version not in (5,6,7):
        return dict(provenance['producerHashes'])
    root=Path(root).resolve()
    result={}
    for name, expected in provenance['producerHashes'].items():
        path=Path(name)
        if '..' in path.parts:
            raise PrerequisiteError('static producer path traversal')
        if path.is_absolute():
            try: path=path.relative_to(root)
            except ValueError: raise PrerequisiteError('static external absolute producer path') from None
        if (not path.parts or path == Path('.')
                or any((root/Path(*path.parts[:index+1])).is_symlink() for index in range(len(path.parts)))
                or (root/path).resolve() != (root/path).absolute()):
            raise PrerequisiteError('static symlink or invalid producer path')
        relative=path.as_posix()
        if relative in result:
            raise PrerequisiteError('static duplicate normalized producer path')
        result[relative]=expected
    return static_extended_archived_producers(result,archive_root if archive_root is not None else root) if version==7 else result


def static_reference_inputs(root, version=1):
    spec = static_spec(version)
    path = Path(root) / spec['reference']
    if path.is_symlink() or digest(path) != spec['digest']:
        raise PrerequisiteError('static frozen provenance mismatch')
    data = json.loads(path.read_text())
    if (data.get('schema') != spec['schema']
            or data.get('status') != 'PASS' or data.get('programSha256') != ORIGINAL_SHA256
            or [p['name'] for p in data['profiles']] != list(spec['counts'])):
        raise PrerequisiteError('static frozen provenance identity')
    result = static_producer_hashes(data, root, version)
    result[spec['reference']] = spec['digest']
    result.update(spec['additional_references'])
    if version == 5:
        interpretation=json.loads((Path(root)/STATIC_THIRTYFOUR_INTERPRETATION).read_text())
        if (interpretation.get('schema') != 'claw-original-static-row-interpretation-v1'
                or interpretation.get('provenanceSha256') != spec['digest']
                or interpretation.get('programSha256') != ORIGINAL_SHA256):
            raise PrerequisiteError('static corrected interpretation identity')
    for row in data['profiles']:
        if row['path'] != row['name'] + '.json.gz':
            raise PrerequisiteError('static shard path')
        name = str(Path(spec['reference']).parent / row['path'])
        shard = Path(root) / name
        if shard.is_symlink() or digest(shard) != row['sha256']:
            raise PrerequisiteError('static frozen shard mismatch')
        logical = gzip.decompress(shard.read_bytes())
        if hashlib.sha256(logical).hexdigest() != row['logicalSha256'] or len(shard.read_bytes()) != row['bytes']:
            raise PrerequisiteError('static logical shard mismatch')
        result[name] = row['sha256']
    for name, expected in result.items():
        path = Path(root) / name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or digest(path) != expected:
            raise PrerequisiteError('static original producer mismatch: ' + name)
    return result


def validate_static_certificate(payload, version=None):
    version = version if version is not None else static_certificate_version(payload)
    spec = static_spec(version)
    def require(ok, message):
        if not ok:
            raise ValueError('invalid static startup certificate: ' + message)
    require(payload.get('command') == spec['command'] and payload.get('status') == 'pass', 'identity')
    modes = payload.get('modes')
    require(isinstance(modes, list) and len(modes) == 2, 'modes')
    for report, sanitized in zip(modes, (True, False)):
        require(isinstance(report, dict), 'mode object')
        require(report.get('status') == 'pass' and report.get('command') == 'native-static-startup'
                and report.get('sanitized') is sanitized and report.get('optimized') is (not sanitized)
                and report.get('native_table_walker') is True and report.get('gameplay') is False
                and type(report.get('checks')) is int and report['checks'] == spec['checks'], 'bounded mode')
        require(type(report.get('reference_version', 1)) is int and report.get('reference_version', 1) == version, 'reference version')
        profiles, controls = report.get('profiles'), report.get('authority_controls')
        require(isinstance(profiles, list) and all(isinstance(p, dict) for p in profiles) and [p.get('profile') for p in profiles] == list(spec['counts']), 'profiles')
        require(isinstance(controls, list) and all(isinstance(p, dict) for p in controls) and [p.get('authority_control') for p in controls] == list(spec['controls']), 'controls')
        for row in profiles + controls:
            control = row.get('authority_control')
            counts = spec['counts'][row['profile']] if not control else spec['control_counts'][control]
            require(row.get('status') == 'pass' and row.get('command') == 'native-static-startup'
                    and row.get('gameplay') is False and row.get('native_table_walker') is True, 'row identity')
            require((control in spec['controls'] and row['profile'] == spec['seed'])
                    if row in controls else control == '', 'authority identity')
            require(all(type(row.get(k)) is int and row[k] == v for k,v in zip(
                spec['count_fields'], counts)), 'counters')
            require(isinstance(row.get('native_artifact_sha256'), str) and re.fullmatch('[0-9a-f]{64}', row['native_artifact_sha256']), 'artifact hash')
            if version >= 4:
                require(stable_hash({field:row.get(field) for field in spec.get('scope_fields',STATIC_SCOPE_FIELDS)}) ==
                    spec['scope_identities'][control or row['profile']], 'reference-only scope identity')



STATIC_SCOPE_FIELDS = ('observed_reference_boundaries', 'reference_only_entry_indices',
    'reference_only_state_indices', 'reference_only_inline_fs_transitions')


def static_scope_inventory(original, artifact):
    """Derive scope from immutable original entries and actual captured boundaries."""
    states = artifact['states']
    final=original.get('schema')=='claw-original-static-startup-final-records-pages-v9'
    lists=final or original.get('schema')=='claw-original-static-startup-list-records-pages-v8'
    extended=original.get('schema') in ('claw-original-static-startup-extended-records-pages-v7','claw-original-static-startup-list-records-pages-v8','claw-original-static-startup-final-records-pages-v9')
    if any(state['function'] in (0x4dbb10,0x4dbb90,0x4db620) and not (extended and (state['function'],state['returnPC']) in {(0x4db620,0x4dc2a8),(0x4dbb10,0x440f63)}) for state in states):
        raise ValueError('static fabricated internal source callback')
    if extended and any(state['function'] in (0x4dc280,0x4dc200,0x4c96b0) for state in states):
        raise ValueError('static fabricated owned factory callback')
    if lists and any(state['function']==0x4fb15d or state['function']==0x4f709b and state['returnPC'] not in ({0x502419,0x503827} if final else {0x502419}) for state in states):
        raise ValueError('static fabricated owned list callback')
    if final and any(state['function'] in (0x4fb3ba,0x4fb376,0x502d5a,0x502d8a,0x4dc3a0)for state in states):
        raise ValueError('static fabricated owned final helper callback')
    boundaries, observed_entries = [], set()
    for index, entry in enumerate(original['entries']):
        for returning in (False,True):
            reference = entry['after'] if returning else entry['before']
            if any(state['function']==entry['function'] and state['returnPC']==entry['returnPC']
                    and state['referenceState']==reference and state['returning'] is returning for state in states):
                boundaries.append(dict(entry=index,state=reference,returning=returning))
                observed_entries.add(index)
    compared = {state['referenceState'] for state in states}
    if any(transition['state'] in compared for transition in original.get('inlineFsTransitions', [])):
        raise ValueError('static fabricated inline FS observation')
    result = dict(observed_reference_boundaries=boundaries,
        reference_only_entry_indices=[i for i in range(len(original['entries'])) if i not in observed_entries],
        reference_only_state_indices=[i for i in range(len(original['states'])) if i not in compared],
        reference_only_inline_fs_transitions=original.get('inlineFsTransitions', []))
    if original.get('schema') in ('claw-original-static-startup-application-shared-pages-v6','claw-original-static-startup-extended-records-pages-v7','claw-original-static-startup-list-records-pages-v8','claw-original-static-startup-final-records-pages-v9'):
        if any(state['function']==0x4a5690 for state in states):
            raise ValueError('static fabricated owned throw callback')
        if any(entry.get('observation')=='original-only-internal' and index in observed_entries
                and (entry['function'],entry['returnPC']) not in ({(0x4f5e89,0x4a2d0b),(0x501f01,0x50235d),(0x501fde,0x502396)} | ({(0x4f6a9a,0x4f837a)} if lists else set()))
                for index,entry in enumerate(original['entries'])):
            raise ValueError('static fabricated owned internal callback')
        observed_physical=set()
        for index,event in enumerate(original['events']):
            matches=[state for state in states if state['physical'] and state['function']==event['function']
                and state['returnPC']==event['returnPC'] and state['referenceState'] in (event['before'],event['after'])]
            if matches:
                if ({state['returning'] for state in matches}!={False,True}
                        or any(state['referenceState']!=(event['after'] if state['returning'] else event['before']) for state in matches)):
                    raise ValueError('static incomplete physical observation pair')
                observed_physical.add(index)
        if observed_physical!=set(range(len(observed_physical))):
            raise ValueError('static skipped physical event')
        result['reference_only_physical_event_indices']=[i for i in range(len(original['events'])) if i not in observed_physical]
    return result


def validate_static_extended_inputs(row, original):
    inputs=original.get('declaredCallerInputs')
    if (not isinstance(inputs,dict) or set(inputs)!={'diagnosticMode4','ebpAnchor'}
            or any(type(v) is not bool for v in inputs.values())
            or row.get('declared_caller_inputs')!=inputs
            or any(type(v) is not bool for v in row.get('declared_caller_inputs',{}).values())):
        raise ValueError('static extended declared caller input policy')
    diagnostic=row['profile']==('final144-string-range-zero-original-mode4' if original.get('schema')=='claw-original-static-startup-final-records-pages-v9' else 'list133-string-range-zero-original-mode4' if original.get('schema')=='claw-original-static-startup-list-records-pages-v8' else 'string-range-malloc-zero-original-mode4')
    if inputs!={'diagnosticMode4':diagnostic,'ebpAnchor':diagnostic}:
        raise ValueError('static extended diagnostic unit policy isolation')


def validate_static_final_state(state, expected):
    fields=('platformPolicyId','platformHistory','versionHistory','desktopDCAttempt','liveDesktopDCs','desktopDCHistory','borrowedIdentityTable','borrowedLookupHistory')
    if any(k not in state or k not in expected or state[k]!=expected[k] for k in fields):
        raise ValueError('static final platform/DC/borrowed state comparison')
    def uint(v):return type(v) is int and 0<=v<=0xffffffff
    def call(row,dc=False):
        keys={'name','returnPC','arguments','result'}|({'live'}if dc else set())
        return (isinstance(row,dict) and set(row)==keys and isinstance(row['name'],str)
            and uint(row['returnPC']) and uint(row['result']) and isinstance(row['arguments'],list)
            and all(uint(v)for v in row['arguments'])
            and (not dc or isinstance(row['live'],list) and row['live'] in ([],[0x79000001])))
    if state['platformPolicyId']!=STATIC_FINAL_POLICY_SHA256:
        raise ValueError('static final platform policy identity')
    if not isinstance(state['platformHistory'],list) or any(not call(r) or r['name'] not in {'GetProcessVersion','GetSystemMetrics','GetDC','GetDeviceCaps','ReleaseDC','GetSysColor','GetSysColorBrush','LoadCursorA'}for r in state['platformHistory']):
        raise ValueError('static final physical history schema')
    if not isinstance(state['versionHistory'],list) or any(not isinstance(r,dict)or set(r)!={'returnPC','result'}or not all(uint(v)for v in r.values()) for r in state['versionHistory']):
        raise ValueError('static final version history schema')
    attempt=state['desktopDCAttempt']
    if attempt is not None and (not isinstance(attempt,dict)or set(attempt)!={'result','phase','acquireReturnPC'}or not uint(attempt['result'])or attempt['result']not in (0,0x79000001)or attempt['phase']not in {'acquired','caps88','caps90','released','release-failed'}or attempt['acquireReturnPC']!=0x4fb3ed):
        raise ValueError('static final DC attempt schema')
    leases=state['liveDesktopDCs']
    if leases not in ([],[dict(handle=0x79000001,kind='desktopDC',hwnd=0,acquireReturnPC=0x4fb3ed)]) or any(type(r['hwnd'])is not int for r in leases):
        raise ValueError('static final DC lease schema')
    if not isinstance(state['desktopDCHistory'],list)or any(not call(r,True)or r['name']not in {'GetDC','GetDeviceCaps','ReleaseDC'}for r in state['desktopDCHistory']):
        raise ValueError('static final DC history schema')
    identities={'brushes':{'15':0x7900100f,'6':0x79001006},'cursors':{'32514':0x7a007f02,'32512':0x7a007f00}}
    if state['borrowedIdentityTable']!=identities or not isinstance(state['borrowedLookupHistory'],list)or any(not call(r)or r['name']not in {'GetSysColorBrush','LoadCursorA'}for r in state['borrowedLookupHistory']):
        raise ValueError('static final borrowed identity/history schema')


def validate_static_final_inputs(row, original):
    # The v9 platform selectors intentionally supersede unused v8 message fields.
    inputs=original.get('platformProfileInputs');declared=original.get('declaredProfileInputs')
    keys={'version','processVersion','scalarPolicy','dcPolicy','releasePolicy','borrowedPolicy','messagePolicy','messageInitial','capsPolicy','physicalStop'}
    if (original.get('schema')!='claw-original-static-startup-final-records-pages-v9'
            or not isinstance(inputs,dict) or set(inputs)!=keys or not isinstance(declared,dict)
            or stable_hash(inputs)!=stable_hash({key:declared.get(key)for key in keys})):
        raise ValueError('static final authoritative policy inputs')
    if (not isinstance(inputs,dict)or row.get('declared_platform_inputs')!=inputs
            or stable_hash(row.get('declared_platform_inputs'))!=stable_hash(inputs)
            or row.get('physical_policy_sha256')!=STATIC_FINAL_POLICY_SHA256
            or original.get('physicalPolicySha256')!=STATIC_FINAL_POLICY_SHA256):
        raise ValueError('static final declared platform policy inputs')


def validate_static_list_state(state, expected):
    """Check actual process-local physical registry and call history."""
    fields=('namedMessages','nextNamedMessage','namedMessageHistory')
    if any(key not in state or key not in expected or state[key]!=expected[key] for key in fields):
        raise ValueError('static list named-message state comparison')
    def identifier(value): return type(value) is int and 0xc000<=value<=0xffff
    def name(value): return isinstance(value,str) and re.fullmatch('(?:[0-9a-f]{2}){1,255}',value) is not None and '00' not in [value[i:i+2] for i in range(0,len(value),2)]
    rows=state['namedMessages']
    if (not isinstance(rows,list) or any(not isinstance(row,dict) or set(row)!={'nameHex','identifier'}
            or not name(row['nameHex']) or not identifier(row['identifier']) for row in rows)
            or [row['identifier'] for row in rows]!=list(range(0xc000,0xc000+len(rows)))
            or len({row['nameHex'] for row in rows})!=len(rows)
            or type(state['nextNamedMessage']) is not int or state['nextNamedMessage']!=0xc000+len(rows)):
        raise ValueError('static list named-message registry schema')
    history=state['namedMessageHistory']
    if not isinstance(history,list) or any(not isinstance(row,dict) or set(row)!={'nameHex','result','reused','inserted','callerReturnPC'}
            or not name(row['nameHex']) or type(row['result']) is not int or not (row['result']==0 or identifier(row['result']))
            or type(row['reused']) is not bool or type(row['inserted']) is not bool or row['reused'] and row['inserted']
            or (row['result']==0)!=(not row['reused'] and not row['inserted'])
            or type(row['callerReturnPC']) is not int or row['callerReturnPC'] not in ({0x4f822d,0x4ffd50} if expected.get('platformPolicyId')==STATIC_FINAL_POLICY_SHA256 else {0x4f822d}) for row in history):
        raise ValueError('static list named-message history schema')


def validate_static_application_state(state, expected):
    """Validate actual joint physical metadata, independently of page hashes."""
    def uint(value): return type(value) is int and 0<=value<=0xffffffff
    fields=('globalHandles','localAllocations','tlsIndices','tlsValues','nextGlobalHandle','nextTlsIndex','lastError','sectionHistory')
    if any(field not in state or field not in expected or state[field]!=expected[field] for field in fields):
        raise ValueError('static joint physical state comparison')
    for field,keys in (('globalHandles',{'handle','data','size','flags','locks'}),('localAllocations',{'address','requested'})):
        if not isinstance(state[field],list) or any(not isinstance(row,dict) or set(row)!=keys or not all(uint(v) for v in row.values()) for row in state[field]):
            raise ValueError('static joint ownership schema')
    if (not isinstance(state['tlsIndices'],list) or not all(uint(v) for v in state['tlsIndices'])
            or not isinstance(state['tlsValues'],dict) or any(not isinstance(k,str) or not k.isdecimal() or not uint(v) for k,v in state['tlsValues'].items())
            or not all(uint(state[k]) for k in ('nextGlobalHandle','nextTlsIndex','lastError'))):
        raise ValueError('static joint TLS/counter schema')
    if not isinstance(state['sectionHistory'],list) or any(not isinstance(row,dict) or set(row)!={'operation','address','bytesPreserved'}
            or row['operation']!='delete' or not uint(row['address']) or row['bytesPreserved'] is not True for row in state['sectionHistory']):
        raise ValueError('static joint section history schema')


def static_registration_inventory(row, original, final_state, memory):
    """Read executed globals/slots, including retired backing at a stopped resize."""
    def word(address):
        page=memory.get(address & ~4095)
        if page is None or address % 4:
            raise ValueError('static registration memory boundary')
        return int.from_bytes(page[address%4096:address%4096+4], 'little')
    base, next_slot=word(0x545fd4),word(0x545fd0)
    expected=original['states'][final_state['referenceState']]
    if base != expected['registryBase'] or next_slot != expected['registryNext'] or next_slot < base or (next_slot-base)%4:
        raise ValueError('static registration executed globals')
    count=(next_slot-base)//4
    if count > len(original['completedRegistrations']) or row['registrations'] != count:
        raise ValueError('static registration executed count')
    callbacks=[word(base+index*4) for index in range(count)]
    if callbacks != original['completedRegistrations'][:count]:
        raise ValueError('static registration executed callback vector')
    return callbacks


def static_evidence(certificate, directory, root, capture=False):
    """Retain both modes and reconstruct all page observations against frozen states."""
    validate_static_certificate(certificate)
    version = static_certificate_version(certificate)
    spec = static_spec(version)
    directory, root = Path(directory), Path(root)
    hashes = {}
    def retain(name, source, expected=None):
        target = directory / name
        source = Path(source) if capture else target
        if source.is_symlink() or not source.is_file() or source.resolve() != source.absolute():
            raise ValueError('static artifact path: ' + name)
        actual = digest(source)
        if expected is not None and actual != expected:
            raise ValueError('static artifact fingerprint: ' + name)
        if capture:
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() != target.resolve():
                shutil.copyfile(source, target)
            if digest(source) != actual or digest(target) != actual:
                raise ValueError('static artifact changed during capture')
        hashes[name] = actual
        return target
    if capture:
        references = static_reference_inputs(root, version)
    else:
        references = json.loads((directory / 'reference-inputs.json').read_text())
    if capture:
        atomic_json(directory / 'reference-inputs.json', references)
    retain('reference-inputs.json', directory / 'reference-inputs.json')
    for name, expected in references.items():
        retain('references/' + name, root / name, expected)
    provenance = json.loads((directory / 'references' / spec['reference']).read_text())
    if digest(directory / 'references' / spec['reference']) != spec['digest']:
        raise ValueError('static captured provenance')
    expected_refs = static_producer_hashes(provenance, root, version, archive_root=directory/'references')
    expected_refs[spec['reference']] = spec['digest']
    expected_refs.update(spec['additional_references'])
    expected_refs.update({str(Path(spec['reference']).parent / r['path']):r['sha256'] for r in provenance['profiles']})
    if references != expected_refs:
        raise ValueError('static captured reference inventory')
    if version == 5:
        corrected=json.loads((directory/'references'/STATIC_THIRTYFOUR_INTERPRETATION).read_text())
        if (corrected.get('provenanceSha256') != spec['digest'] or corrected.get('programSha256') != ORIGINAL_SHA256
                or corrected.get('schema') != 'claw-original-static-row-interpretation-v1'):
            raise ValueError('static captured corrected interpretation identity')
    originals = {}
    for row in provenance['profiles']:
        raw = gzip.decompress((directory / 'references' / Path(spec['reference']).parent / row['path']).read_bytes())
        if hashlib.sha256(raw).hexdigest() != row['logicalSha256']:
            raise ValueError('static captured logical reference')
        originals[row['name']] = json.loads(raw)
        if version >= 5 and originals[row['name']].get('mode') != 'moving':
            raise ValueError('static declared moving allocator policy')
    for report, mode in zip(certificate['modes'], ('sanitized','optimized')):
        prefix = mode + '/'
        cp = Path(report['certificate'])
        key = cp.parent.name
        if not re.fullmatch('[0-9a-f]{64}', key) or cp != root.resolve() / 'work/native-static-startup-cache' / key / 'certificate.json':
            raise ValueError('static cache identity')
        build = json.loads(retain(prefix+'build-certificate.json', cp).read_text())
        if (not isinstance(build, dict) or hashlib.sha256(json.dumps(build,sort_keys=True).encode()).hexdigest() != key
                or build.get('reference_provenance') != spec['digest']
                or build.get('original') != ORIGINAL_SHA256 or not build.get('inputs')):
            raise ValueError('static build identity')
        if version==7:
            archive=json.loads((directory/'references'/STATIC_EXTENDED_ARCHIVE_MANIFEST).read_text())
            if (any(build['inputs'].get(row['path'])!=row['sha256'] for row in archive['current_inputs']) or any(build['inputs'].get(name)!=expected for name,expected in expected_refs.items() if name.startswith(STATIC_EXTENDED_ARCHIVE_ROOT+'/'))):
                raise ValueError('static missing or changed current native producer inputs')
        if version==8:
            archive=static_list_archived_producers(provenance,directory/'references')
            if any(build['inputs'].get(name)!=value for name,value in archive.items()) or any(name not in build['inputs'] for name in ('Tests/clawparity/env.py','Tests/clawparity/kernel.py','tools/claw/milestone.py')):
                raise ValueError('static missing list archived or current native inputs')
        if version==9:
            archive=static_final_archived_producers(provenance,directory/'references')
            if any(build['inputs'].get(name)!=value for name,value in archive.items()) or any(name not in build['inputs'] for name in ('Tests/clawparity/env.py','Tests/clawparity/kernel.py','tools/claw/milestone.py')):
                raise ValueError('static missing final archived or current native inputs')
        for flags in ('cflags','sflags'):
            values = build[flags]
            sanitizer = '-fsanitize=address,undefined' if flags == 'cflags' else '-sanitize=address'
            if (mode == 'sanitized') != (sanitizer in values):
                raise ValueError('static build sanitizer mode')
            if (mode == 'optimized') != any(x in ('-O','-O2') for x in values):
                raise ValueError('static build optimization mode')
        binary_hash = retain(prefix+'binary.sha256', cp.parent/'binary.sha256').read_text()
        retain(prefix+'native-check', cp.parent/'check', binary_hash)
        retain(prefix+'ClawCanonicalDispatch.h', cp.parent/'ClawCanonicalDispatch.h', build['registry'])
        for name, expected in build['inputs'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('static build input path')
            if capture and digest(root/name) != expected:
                raise ValueError('static current compiled input mismatch')
            retain(prefix+'snapshot/'+name, cp.parent/'snapshot'/name, expected)
        if version==9:
            from .static_build_inputs import load_final_build
            reconstructed=load_final_build(directory/prefix/'snapshot')
            if (build.get('selected_build')!=reconstructed['membership']
                    or build['registry']!=reconstructed['membership']['registry_sha256']
                    or build['inputs']!={name:hashlib.sha256(data).hexdigest()for name,data in reconstructed['inputs'].items()}):
                raise ValueError('static final selected build reconstruction')
        report_path = Path(report['report_path'])
        if capture and report_path != directory.resolve()/(spec['report_prefix']+mode+'-report.json'):
            raise ValueError('static invocation report path')
        if json.loads(retain(prefix+'report.json', report_path).read_text()) != report:
            raise ValueError('static publisher report mismatch')
        count = 0
        for row in report['profiles'] + report['authority_controls']:
            action = row['authority_control']
            name = ('authority-'+action if action else 'golden-'+row['profile'])+'.native.json'
            if Path(row['native_artifact']) != cp.parent/name:
                raise ValueError('static native artifact identity')
            artifact = json.loads(retain(prefix+name,row['native_artifact'],row['native_artifact_sha256']).read_text())
            expected_result = {k:v for k,v in row.items() if k not in ('reference_sha256','native_artifact','native_artifact_sha256')}
            if not isinstance(artifact, dict) or artifact.get('schema') != 'claw-native-static-startup-pages-v1' or artifact.get('profile') != row['profile'] or artifact.get('result') != expected_result:
                raise ValueError('static native result identity')
            identities = [[state[k] for k in ('function','returnPC','returning','completed','physical','referenceState')] for state in artifact['states']]
            if stable_hash(identities) != spec['identities'][action or row['profile']]:
                raise ValueError('static observation identity/order')
            original = originals[row['profile']]
            if version >= 4:
                scope = static_scope_inventory(original, artifact)
                if (any(row[field] != scope[field] for field in spec.get('scope_fields',STATIC_SCOPE_FIELDS))
                        or stable_hash(scope) != spec['scope_identities'][action or row['profile']]):
                    raise ValueError('static reference-only scope reconstruction')
            frozen = next(r for r in provenance['profiles'] if r['name']==row['profile'])
            if not action and row.get('reference_sha256') != frozen['sha256']:
                raise ValueError('static row reference')
            pages = []
            for page in artifact['pages']:
                data = bytes.fromhex(page['bytes'])
                if len(data) != 4096 or hashlib.sha256(data).hexdigest() != page['sha256']:
                    raise ValueError('static page hash')
                pages.append(data)
            table_control = action.endswith('-table')
            mutations = [i for i, state in enumerate(artifact['states']) if 'authorityMutation' in state]
            if mutations != ([len(artifact['states'])-1] if table_control else []):
                raise ValueError('static authority mutation placement')
            memory = {}
            for index,state in enumerate(artifact['states']):
                mem = state['memory']
                parent = mem['parent']
                if ((parent is not None if index == 0 else type(parent) is not int or parent != index-1)
                        or len({a for a,_ in mem['pageChanges']}) != len(mem['pageChanges'])):
                    raise ValueError('static state parent/deltas')
                for address,pid in mem['pageChanges']:
                    if type(address) is not int or address % 4096 or type(pid) is not int or not 0 <= pid < len(pages):
                        raise ValueError('static page destination')
                    memory[address] = pages[pid]
                for region in mem['ranges']:
                    data = b''.join(memory[a] for a in range(region['address'],region['address']+region['size'],4096))
                    if len(data) != region['size'] or hashlib.sha256(data).hexdigest() != region['sha256']:
                        raise ValueError('static state range')
                    if version >= 4 and region['name']=='thread' and int.from_bytes(data[:4], 'little') != state['cpu'].get('fsHead'):
                        raise ValueError('static raw FS/CPU coherence')
                ref = state['referenceState']
                if type(ref) is not int or not 0 <= ref < len(original['states']):
                    raise ValueError('static reference state index')
                expected = original['states'][ref]
                expected_ranges = expected['memory']['ranges']
                if 'authorityMutation' in state:
                    mutation = state['authorityMutation']
                    if (not table_control or version not in (3,4,5,6,7,8,9) or not isinstance(mutation, dict)
                            or set(mutation) != set(STATIC_TABLE_MUTATION)
                            or any(type(value) is not int for value in mutation.values())
                            or mutation != STATIC_TABLE_MUTATION
                            or state['function'] != 0x50372c or state['returnPC'] != 0x503727
                            or state['physical'] is not False
                            or state['returning'] is not action.startswith('return')):
                        raise ValueError('static authority mutation identity')
                    expected_ranges = [dict(region) for region in expected_ranges]
                    image = next(region for region in expected_ranges if region['name'] == 'image')
                    original_memory = {}
                    for original_state in original['states'][:ref+1]:
                        for address,pid in original_state['memory']['pageChanges']:
                            original_memory[address] = bytes.fromhex(original['pages'][pid]['bytes'])
                    image_bytes = bytearray(b''.join(original_memory[address] for address in
                        range(image['address'],image['address']+image['size'],4096)))
                    if hashlib.sha256(image_bytes).hexdigest() != image['sha256']:
                        raise ValueError('static original authority image reconstruction')
                    offset = STATIC_TABLE_MUTATION['address'] - image['address']
                    before = STATIC_TABLE_MUTATION['before'].to_bytes(4, 'little')
                    if offset < 0 or image_bytes[offset:offset+4] != before:
                        raise ValueError('static original authority table slot')
                    image_bytes[offset:offset+4] = STATIC_TABLE_MUTATION['after'].to_bytes(4, 'little')
                    image['sha256'] = hashlib.sha256(image_bytes).hexdigest()
                cpu = state['cpu']
                cpu_fields = {'eax','ebx','ecx','edx','esi','edi','ebp','esp','eip','eflags','fsHead'}
                if (not isinstance(cpu, dict) or set(cpu) != cpu_fields
                        or any(type(value) is not int or not 0 <= value <= 0xffffffff for value in cpu.values())):
                    raise ValueError('static CPU field schema')
                allocations, sections = state['allocations'], state['sections']
                for ledger, numeric, boolean in (
                        (allocations, {'address','requested','capacity','identity'}, 'live'),
                        (sections, {'address','depth','owner'}, 'initialized')):
                    if (not isinstance(ledger, list) or any(
                            not isinstance(item, dict) or set(item) != numeric | {boolean}
                            or type(item[boolean]) is not bool
                            or any(type(item[field]) is not int or item[field] < 0 for field in numeric)
                            for item in ledger)):
                        raise ValueError('static ownership ledger field schema')
                if (state['cpu'] != expected['cpu'] or state['sections'] != expected['sections']
                        or mem['ranges'] != expected_ranges
                        or state['allocations'] != [{k:a[k] for k in ('address','requested','capacity','identity','live')} for a in expected['allocations']]):
                    raise ValueError('static native state comparison')
                if version>=6: validate_static_application_state(state,expected)
                if version>=8: validate_static_list_state(state,expected)
                if version==9: validate_static_final_state(state,expected)
                count += 1
            if version >= 5:
                static_registration_inventory(row, original, artifact['states'][-1], memory)
            if version>=6:
                if version>=7: validate_static_extended_inputs(row,original)
                if version==9: validate_static_final_inputs(row,original)
                missing=None
                if (row.get('missing_native_dependency')!=missing
                        or (missing is not None and type(row['missing_native_dependency']) is not int)):
                    raise ValueError('static joint missing dependency classification')
        if count != spec['states']:
            raise ValueError('static observation count')
    return hashes


def crt_evidence(certificate, directory, root, capture=False):
    """Validate/capture only the invocation's named artifacts, never shared reports."""
    directory = Path(directory)
    build_path = Path(certificate['certificate'])
    if (build_path.is_symlink() or build_path.name != 'certificate.json'
            or build_path.parent.name != certificate['cache_key']
            or build_path.parent.parent.resolve() != Path(root).resolve() / 'work/native-crt-exit-registry-cache'
            or build_path.resolve() != Path(root).resolve() / 'work/native-crt-exit-registry-cache' / certificate['cache_key'] / 'certificate.json'):
        raise ValueError('CRT build certificate path')
    targets = {'build-certificate.json': (build_path, certificate['certificate_sha256'])}
    saved_path = build_path if capture else directory / 'build-certificate.json'
    saved = json.loads(saved_path.read_text())
    build = saved.get('certificate')
    if (not isinstance(build, dict) or build.get('whole_leaves') is not True
            or build.get('sanitized') is not True or build.get('optimized') is not False
            or build.get('original') != ORIGINAL_SHA256
            or hashlib.sha256(json.dumps(build, sort_keys=True).encode()).hexdigest() != certificate['cache_key']):
        raise ValueError('CRT build certificate identity')
    if not isinstance(saved.get('binary'), str) or not re.fullmatch('[0-9a-f]{64}', saved['binary']):
        raise ValueError('CRT binary digest')
    if (type(build.get('schema')) is not int or build['schema'] != 1
            or build.get('command') != 'native-crt-exit-registry'
            or build.get('root_sites') != certificate.get('scope')):
        raise ValueError('CRT build scope')
    if (not isinstance(build.get('cpp'), list) or not isinstance(build.get('swift'), list)
            or '-fsanitize=address,undefined' not in build['cpp']
            or '-sanitize=address' not in build['swift']
            or any(isinstance(x, str) and re.fullmatch('-O.*', x) for x in build['cpp'] + build['swift'])):
        raise ValueError('CRT compiler sanitizer mode')
    edges = build.get('edges')
    if (not isinstance(edges, dict) or edges.get('status') != 'pass'
            or any(type(edges.get(k)) is not int or edges[k] != v for k, v in
                   dict(edges=23, source_entries=8, prepared_roots=8, physical_services=7,
                        missing_source_stops=1, registration_leaves=126).items())
            or type(edges.get('rejected_metadata_mutations')) is not int
            or edges['rejected_metadata_mutations'] < 49
            or edges.get('original_registration_order_sha256') != '4d24cb562a78c6ed56e166257c3141f68d262e6d8798b9607344413ff2e5ed63'):
        raise ValueError('CRT compiled edge contract')
    if (not isinstance(build.get('inputs'), dict) or not build['inputs']
            or any(not isinstance(k, str) or Path(k).is_absolute() or '..' in Path(k).parts
                   or not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v)
                   for k, v in build['inputs'].items())):
        raise ValueError('CRT compiled inputs missing or invalid')
    targets['native-check'] = (build_path.parent / 'check', saved['binary'])
    negatives = saved.get('negative_binaries')
    kinds = {'callback', 'parentPC', 'argumentStore', 'returnStore', 'frame', 'bodyEAX', 'cleanupECX', 'cleanupFlags'}
    if not isinstance(negatives, dict) or set(negatives) != kinds:
        raise ValueError('CRT negative binary identities')
    for kind, artifact in negatives.items():
        for suffix, field in (('', 'binary'), ('.cpp', 'source')):
            if not isinstance(artifact, dict) or not isinstance(artifact.get(field), str) or not re.fullmatch('[0-9a-f]{64}', artifact[field]):
                raise ValueError('CRT negative artifact digest')
            name = 'negative-' + kind + suffix
            targets[name] = (build_path.parent / name, artifact[field])
    for profile in certificate['profiles']:
        path = Path(profile['native_snapshot'])
        if path.name != profile['profile'] + '-native.json' or '..' in path.parts:
            raise ValueError('CRT invocation snapshot identity')
        # A copied resume retains the original invocation path. It is never
        # dereferenced on resume; the captured local artifact is checked.
        if capture and (path.is_symlink()
                or path.parent != directory.resolve() / 'crt-native-whole-snapshots/sanitized'
                or path.resolve().parent != path.parent):
            raise ValueError('CRT invocation snapshot path')
        targets['crt-native-whole-snapshots/sanitized/' + path.name] = (path, profile['native_snapshot_sha256'])
    report_name = 'crt-native-whole-sanitized-report.json'
    report_path = Path(certificate['report_path']) if capture else directory / report_name
    if capture and report_path != directory.resolve() / report_name:
        raise ValueError('CRT invocation report path')
    if report_path.is_symlink() or json.loads(report_path.read_text()) != certificate:
        raise ValueError('CRT invocation report mismatch')
    targets[report_name] = (report_path, digest(report_path))
    hashes = {}
    for name, (source, expected) in targets.items():
        target = directory / name
        if capture:
            if source.is_symlink() or digest(source) != expected:
                raise ValueError('CRT artifact fingerprint mismatch: ' + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() != target.resolve():
                shutil.copyfile(source, target)
            if digest(source) != expected:
                raise ValueError('CRT artifact changed during capture: ' + name)
        if target.is_symlink() or digest(target) != expected:
            raise ValueError('CRT captured artifact fingerprint mismatch: ' + name)
        hashes[name] = expected
    return hashes


def command_for(check_id):
    return {'project': [sys.executable, '-m', 'tools.claw.gen_project', 'check'],
            'source_graph': ['scripts/check-native-graph-replay.sh'],
            'tls_manager_source': ['scripts/check-native-mfc-tls-manager-source.sh'],
            'tls_values_source': ['scripts/check-native-mfc-tls-values-source.sh'],
            'cold_module_source': ['scripts/check-native-mfc-cold-module.sh'],
            'application_thread_source': ['scripts/check-native-mfc-application-thread-source.sh'],
            'application_object_source': ['scripts/check-native-mfc-application-object.sh'],
            'crt_registry_source': ['scripts/check-native-crt-exit-registry.sh'],
            'static_startup_prefix': [sys.executable, '-c', STATIC_PUBLISH],
            'static_startup_three': [sys.executable, '-c', STATIC_THREE_PUBLISH],
            'static_startup_seven': [sys.executable, '-c', STATIC_SEVEN_PUBLISH],
            'static_startup_fifteen': [sys.executable, '-c', STATIC_FIFTEEN_PUBLISH],
            'static_startup_thirtyfour': [sys.executable, '-c', STATIC_THIRTYFOUR_PUBLISH],
            'static_startup_application': [sys.executable, '-c', STATIC_APPLICATION_PUBLISH],
            'static_startup_extended': [sys.executable, '-c', STATIC_EXTENDED_PUBLISH],
            'static_startup_list': [sys.executable, '-c', STATIC_LIST_PUBLISH],
            'static_startup_final': [sys.executable, '-c', STATIC_FINAL_PUBLISH],
            'startup_prefix': ['scripts/check-native-application-pregraphics.sh']}[check_id]


def stop_process(process):
    # The private session/process group also contains the check's descendants.
    # Kill the group even if its direct parent exits before a TERM-ignoring child.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait(); return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def execute_check(check_id, run_dir, timeout, root=ROOT):
    directory = Path(run_dir) / check_id
    directory.mkdir()
    result = {'id': check_id, 'status': 'failed', 'exit_code': None}
    start = time.monotonic()
    with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
        try:
            process = subprocess.Popen(command_for(check_id), cwd=root, stdout=stdout, stderr=stderr,
                                       env=controlled_environment(os.environ, directory, check_id), start_new_session=True)
            try:
                result['exit_code'] = process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
                result.update(status='unknown', reason='interrupted' if isinstance(error, KeyboardInterrupt) else 'timeout')
            finally:
                # A crashed or successful parent can still leave child processes.
                # Finish only this invocation's private group before hashing logs.
                stop_process(process)
        except OSError as error:
            result['reason'] = type(error).__name__
    result['wall_seconds'] = round(time.monotonic() - start, 6)
    certificate = None
    if result['exit_code'] == 0:
        try:
            certificate = read_certificate(check_id, directory / 'stdout.log')
            if check_id == 'startup_prefix' and digest(directory / 'reference.json') != certificate['reference_sha256']:
                raise ValueError('startup reference artifact fingerprint mismatch')
            if check_id in STATIC_CHECKS:
                result['evidence'] = static_evidence(certificate, directory, root, capture=True)
            if check_id == 'crt_registry_source':
                result['evidence'] = crt_evidence(certificate, directory, root, capture=True)
            result['status'] = 'verified'
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            result['reason'] = str(error)
    atomic_json(directory / 'result.json', certificate)
    result['certificate'] = certificate
    result['artifacts'] = {name: digest(directory / (name + ('.json' if name == 'result' else '.log')))
                           for name in ('stdout', 'stderr', 'result')}
    return result


def milestones():
    return [{'id': name, 'status': 'unimplemented', 'reason': 'no connected-flow acceptance publisher'}
            for name in ('startup_complete', 'menu', 'new_game', 'level1', 'gameplay', 'death_checkpoint', 'results')]


def read_record(record_path, root):
    if Path(record_path).is_symlink() or Path(record_path).parent.is_symlink():
        raise ValueError('run records must not be symlinks')
    path = Path(record_path).resolve()
    base = (Path(root) / 'work/milestone').resolve()
    if path.name != 'run.json' or path.parent.parent != base:
        raise ValueError('record must be an own work/milestone/<uuid>/run.json')
    uuid.UUID(path.parent.name)
    record = json.loads(path.read_text())
    if not isinstance(record, dict):
        raise ValueError('run record must be an object')
    if record.get('schema') != SCHEMA or record.get('command') != 'milestone-run' or record.get('run_id') != path.parent.name:
        raise ValueError('invalid own run record')
    selection, inputs, identity = record.get('selection'), record.get('inputs'), record.get('toolchain')
    if not isinstance(selection, list) or not selection or any(type(c) is not str or c not in CHECKS for c in selection) or selection != select_checks(selection):
        raise ValueError('invalid record selection')
    if not isinstance(inputs, dict) or not inputs or any(type(p) is not str or type(h) is not str or not re.fullmatch('[0-9a-f]{64}', h) for p, h in inputs.items()):
        raise ValueError('invalid record inputs')
    if not isinstance(identity, dict) or not identity or any(type(k) is not str or type(v) is not str for k, v in identity.items()):
        raise ValueError('invalid record toolchain')
    if not isinstance(record.get('freshness'), dict) or record['freshness'].get('status') not in ('matching', 'stale'):
        raise ValueError('invalid record freshness')
    checks = record.get('checks')
    if not isinstance(checks, list) or any(not isinstance(c, dict) or c.get('id') not in selection or c.get('status') not in ('verified', 'failed', 'unknown') for c in checks):
        raise ValueError('invalid record checks')
    if len({c['id'] for c in checks}) != len(checks) or record.get('checks_status') not in ('verified', 'failed'):
        raise ValueError('invalid record check summary')
    if record.get('fingerprint') != fingerprint(record['selection'], record['inputs'], record['toolchain']):
        raise ValueError('record fingerprint mismatch')
    if record.get('record_sha256') != stable_hash({k: v for k, v in record.items() if k != 'record_sha256'}):
        raise ValueError('run record content checksum mismatch')
    return path, record


def run_checks(checks, *, resume=None, timeout=None, root=ROOT, toolchain=None):
    checks = select_checks(checks); root = Path(root)
    base = root / 'work/milestone'; base.mkdir(parents=True, exist_ok=True)
    with (base / 'run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'schema': SCHEMA, 'command': 'milestone-run', 'checks_status': 'blocked', 'reason': 'another milestone run holds the lock', 'milestone_status': 'unimplemented'}
        inputs = input_inventory(root, checks)
        identity = toolchain if toolchain is not None else toolchain_identity(root)
        key = fingerprint(checks, inputs, identity)
        prior_path, prior = read_record(resume, root) if resume else (None, {})
        reuse = prior.get('fingerprint') == key and prior.get('freshness', {}).get('status') == 'matching'
        run_id = str(uuid.uuid4()); directory = base / run_id; directory.mkdir()
        record = {'schema': SCHEMA, 'command': 'milestone-run', 'run_id': run_id,
                  'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'selection': checks, 'inputs': inputs, 'toolchain': identity, 'fingerprint': key,
                  'checks': [], 'milestones': milestones(), 'milestone_status': 'unimplemented',
                  'device_acceptance': {'status': 'unknown', 'reason': 'no target-device acceptance in this runner'},
                  'limits': [LIMIT, 'App/GameData is generated output; original selected asset inputs are hashed separately.',
                             'Startup compiles C++ objects in each attempt; no shared object-cache speedup is claimed.']}
        for check_id in checks:
            previous = next((c for c in prior.get('checks', []) if c.get('id') == check_id), None)
            if reuse and previous and artifacts_valid(previous, prior_path.parent):
                (directory / check_id).mkdir()
                for name in ('stdout.log', 'stderr.log', 'result.json') + (('reference.json',) if check_id == 'startup_prefix' else ()):
                    shutil.copyfile(prior_path.parent / check_id / name, directory / check_id / name)
                for name in previous.get('evidence', {}):
                    target = directory / check_id / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(prior_path.parent / check_id / name, target)
                checked = dict(previous, reused_from=prior['run_id'])
            else:
                checked = execute_check(check_id, directory,
                                        timeout if timeout is not None else CHECK_TIMEOUTS.get(check_id, DEFAULT_CHECK_TIMEOUT), root)
            if check_id == 'source_graph' and checked['status'] == 'verified' and any(
                    checked['certificate']['reference_sha256'][p] != inputs[p] for p in GOLDENS):
                checked.update(status='unknown', reason='source graph reference fingerprint mismatch')
            if check_id == 'tls_manager_source' and checked['status'] == 'verified' and (
                    checked['certificate']['reference_sha256'] != inputs[MANAGER_REFERENCE]):
                checked.update(status='unknown', reason='manager reference fingerprint mismatch')
            if check_id == 'tls_values_source' and checked['status'] == 'verified' and (
                    checked['certificate']['reference_sha256'] != inputs[VALUES_REFERENCE]):
                checked.update(status='unknown', reason='TLS values reference fingerprint mismatch')
            if check_id == 'cold_module_source' and checked['status'] == 'verified' and (
                    checked['certificate']['reference_sha256'] != inputs[MODULE_REFERENCE]):
                checked.update(status='unknown', reason='cold module reference fingerprint mismatch')
            if check_id == 'application_thread_source' and checked['status'] == 'verified' and (
                    checked['certificate']['reference_sha256'] != inputs[APPLICATION_THREAD_REFERENCE]):
                checked.update(status='unknown', reason='application thread reference fingerprint mismatch')
            if check_id == 'application_object_source' and checked['status'] == 'verified' and (
                    checked['certificate']['reference_sha256'] != inputs[APPLICATION_OBJECT_REFERENCE]):
                checked.update(status='unknown', reason='application object reference fingerprint mismatch')
            if check_id in STATIC_CHECKS and checked['status'] == 'verified':
                for mode in ('sanitized', 'optimized'):
                    build = json.loads((directory / check_id / mode / 'build-certificate.json').read_text())
                    if any(inputs.get(name) != value for name, value in build['inputs'].items()):
                        checked.update(status='unknown', reason='static compiled input fingerprint mismatch')
                    if (build.get('clang') != identity.get('clang') or build.get('swift') != identity.get('swift')
                            or identity.get('sdk') not in build.get('cflags', [])
                            or identity.get('sdk') not in build.get('sflags', [])):
                        checked.update(status='unknown', reason='static compiled toolchain fingerprint mismatch')
            if check_id == 'crt_registry_source' and checked['status'] == 'verified' and (
                    checked['certificate']['reference_provenance_sha256'] != inputs[CRT_REFERENCE]):
                checked.update(status='unknown', reason='CRT reference fingerprint mismatch')
            if check_id == 'crt_registry_source' and checked['status'] == 'verified':
                build = json.loads((directory / check_id / 'build-certificate.json').read_text())['certificate']
                if any(inputs.get(name) != value for name, value in build.get('inputs', {}).items()):
                    checked.update(status='unknown', reason='CRT compiled input fingerprint mismatch')
            record['checks'].append(checked)
            if checked.get('reason') == 'interrupted':
                break
        try:
            matching = input_inventory(root, checks) == inputs and (toolchain is not None or toolchain_identity(root) == identity)
        except (OSError, ValueError, subprocess.SubprocessError):
            matching = False
        record['freshness'] = {'status': 'matching' if matching else 'stale', 'scope': LIMIT}
        if not matching:
            for check in record['checks']:
                if check['status'] == 'verified':
                    check.update(status='unknown', reason='inputs changed during execution')
        record['checks_status'] = 'verified' if len(record['checks']) == len(checks) and all(c['status'] == 'verified' for c in record['checks']) else 'failed'
        record['frontiers'] = [{'kind': 'observed', 'check': c['id'], 'profile': p['name'], 'stop': p['stop']}
                               for c in record['checks'] if c['id'] == 'startup_prefix' and c['status'] == 'verified'
                               for p in c['certificate']['profiles']]
        record['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record['record_sha256'] = stable_hash(record)
        atomic_json(directory / 'run.json', record)
        return dict(record, record_path=str(directory / 'run.json'))


def status(record_path, root=ROOT):
    path, record = read_record(record_path, root)
    try:
        inputs_match = input_inventory(root, record['selection']) == record['inputs']
        tools_match = toolchain_identity(root) == record['toolchain']
    except (OSError, ValueError, subprocess.SubprocessError):
        inputs_match = tools_match = False
    valid = bool(record.get('checks')) and all(artifacts_valid(check, path.parent, require_verified=False) for check in record['checks'])
    return {'schema': SCHEMA, 'command': 'milestone-status', 'record_path': str(path),
            'checks_status': record['checks_status'] if inputs_match and tools_match and valid else 'unknown',
            'freshness': 'matching' if inputs_match and tools_match and valid else 'stale_or_invalid',
            'milestone_status': 'unimplemented', 'milestones': milestones(),
            'frontiers': record.get('frontiers', []) if inputs_match and tools_match and valid else [],
            'device_acceptance': {'status': 'unknown'}, 'limits': [LIMIT]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'run', 'status'))
    parser.add_argument('--check', action='append', choices=CHECKS)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--record', type=Path)
    parser.add_argument('--timeout', type=float, default=None)
    args = parser.parse_args(argv)
    if args.timeout is not None and not 0 < args.timeout < float('inf'):
        parser.error('--timeout must be positive and finite')
    try:
        checks = select_checks(args.check)
        if args.action == 'status':
            if not args.record:
                parser.error('status requires --record')
            result = status(args.record)
        elif args.action == 'run':
            result = run_checks(checks, resume=args.resume, timeout=args.timeout)
        else:
            inputs = input_inventory(ROOT, checks); identity = toolchain_identity()
            result = {'schema': SCHEMA, 'command': 'milestone-plan', 'checks_status': 'not_run',
                      'selection': checks, 'commands': {c: command_for(c) for c in checks},
                      'fingerprint': fingerprint(checks, inputs, identity), 'inputs': inputs, 'toolchain': identity,
                      'milestone_status': 'unimplemented', 'milestones': milestones(), 'limits': [LIMIT]}
        print(json.dumps(result, sort_keys=True))
        return 0 if result['checks_status'] in ('verified', 'not_run') else 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'schema': SCHEMA, 'command': 'milestone-' + args.action, 'checks_status': 'blocked',
                          'milestone_status': 'unimplemented', 'reason': str(error)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
