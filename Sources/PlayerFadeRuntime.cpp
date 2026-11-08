#include "PlayerFadeRuntime.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
namespace {
// Bounded actual4f1b30(x,2) results captured through original x87 bodies.
static constexpr uint64_t squareBits[1025]={
    0x0000000000000000ULL,0x3ff0000000000000ULL,0x4010000000000000ULL,0x4022000000000001ULL,0x4030000000000000ULL,0x4038fffffffffffeULL,
    0x4041ffffffffffffULL,0x4048800000000001ULL,0x4050000000000000ULL,0x4054400000000002ULL,0x4059000000000003ULL,0x405e400000000006ULL,
    0x4062000000000002ULL,0x4065200000000000ULL,0x40687ffffffffffcULL,0x406c200000000002ULL,0x4070000000000000ULL,0x4072100000000004ULL,
    0x40743ffffffffffeULL,0x40768ffffffffffeULL,0x4079000000000003ULL,0x407b900000000004ULL,0x407e400000000001ULL,0x4080880000000001ULL,
    0x4082000000000005ULL,0x408387fffffffffdULL,0x4085200000000004ULL,0x4086c80000000005ULL,0x40887ffffffffffcULL,0x408a480000000006ULL,
    0x408c200000000002ULL,0x408e080000000007ULL,0x4090000000000000ULL,0x4091040000000000ULL,0x4092100000000004ULL,0x409323ffffffffffULL,
    0x40943ffffffffffeULL,0x4095640000000003ULL,0x40968ffffffffffeULL,0x4097c40000000003ULL,0x4099000000000003ULL,0x409a440000000001ULL,
    0x409b900000000004ULL,0x409ce40000000000ULL,0x409e400000000001ULL,0x409fa40000000001ULL,0x40a0880000000001ULL,0x40a1420000000002ULL,
    0x40a2000000000005ULL,0x40a2c20000000001ULL,0x40a387fffffffffdULL,0x40a4520000000004ULL,0x40a5200000000004ULL,0x40a5f20000000004ULL,
    0x40a6c80000000005ULL,0x40a7a20000000003ULL,0x40a8800000000005ULL,0x40a9620000000005ULL,0x40aa47fffffffffdULL,0x40ab320000000003ULL,
    0x40ac200000000002ULL,0x40ad120000000005ULL,0x40ae080000000007ULL,0x40af020000000004ULL,0x40b0000000000000ULL,0x40b080ffffffffffULL,
    0x40b1040000000000ULL,0x40b188fffffffffdULL,0x40b2100000000004ULL,0x40b2990000000007ULL,0x40b3240000000006ULL,0x40b3b10000000001ULL,
    0x40b43ffffffffffeULL,0x40b4d10000000003ULL,0x40b564000000000aULL,0x40b5f8fffffffffcULL,0x40b6900000000005ULL,0x40b7290000000005ULL,
    0x40b7c40000000003ULL,0x40b8610000000002ULL,0x40b8fffffffffffaULL,0x40b9a10000000005ULL,0x40ba44000000000aULL,0x40bae90000000007ULL,
    0x40bb8ffffffffffbULL,0x40bc390000000009ULL,0x40bce40000000000ULL,0x40bd910000000006ULL,0x40be40000000000bULL,0x40bef0ffffffffffULL,
    0x40bfa40000000001ULL,0x40c02c8000000001ULL,0x40c0880000000001ULL,0x40c0e48000000003ULL,0x40c1420000000002ULL,0x40c1a08000000000ULL,
    0x40c1ffffffffffffULL,0x40c2608000000001ULL,0x40c2c20000000007ULL,0x40c3247fffffffffULL,0x40c3880000000004ULL,0x40c3ec8000000006ULL,
    0x40c451fffffffffdULL,0x40c4b88000000001ULL,0x40c51ffffffffffdULL,0x40c5887ffffffffeULL,0x40c5f1fffffffffcULL,0x40c65c7ffffffffcULL,
    0x40c6c80000000005ULL,0x40c7347ffffffffdULL,0x40c7a20000000003ULL,0x40c8108000000002ULL,0x40c87ffffffffffcULL,0x40c8f0800000000aULL,
    0x40c9620000000005ULL,0x40c9d48000000005ULL,0x40ca47fffffffffdULL,0x40cabc8000000003ULL,0x40cb320000000003ULL,0x40cba88000000002ULL,
    0x40cc200000000002ULL,0x40cc98800000000bULL,0x40cd120000000005ULL,0x40cd8c8000000000ULL,0x40ce080000000007ULL,0x40ce84800000000aULL,
    0x40cf020000000004ULL,0x40cf808000000006ULL,0x40d0000000000000ULL,0x40d0403fffffffffULL,0x40d080ffffffffffULL,0x40d0c23fffffffffULL,
    0x40d1040000000000ULL,0x40d1464000000002ULL,0x40d188fffffffffdULL,0x40d1cc4000000006ULL,0x40d2100000000004ULL,0x40d2544000000004ULL,
    0x40d2990000000007ULL,0x40d2de4000000001ULL,0x40d323ffffffffffULL,0x40d36a4000000001ULL,0x40d3b10000000001ULL,0x40d3f83ffffffffdULL,
    0x40d4400000000005ULL,0x40d4884000000000ULL,0x40d4d10000000003ULL,0x40d51a4000000000ULL,0x40d563fffffffffbULL,0x40d5ae4000000004ULL,
    0x40d5f8fffffffffcULL,0x40d6444000000005ULL,0x40d6900000000005ULL,0x40d6dc4000000003ULL,0x40d7290000000005ULL,0x40d7764000000008ULL,
    0x40d7c40000000003ULL,0x40d8124000000000ULL,0x40d8610000000002ULL,0x40d8b04000000003ULL,0x40d8fffffffffffaULL,0x40d9504000000007ULL,
    0x40d9a0fffffffffcULL,0x40d9f24000000005ULL,0x40da44000000000aULL,0x40da963ffffffff9ULL,0x40dae90000000007ULL,0x40db3c4000000006ULL,
    0x40db900000000004ULL,0x40dbe44000000000ULL,0x40dc390000000009ULL,0x40dc8e400000000eULL,0x40dce40000000000ULL,0x40dd3a400000000aULL,
    0x40dd910000000006ULL,0x40dde8400000000cULL,0x40de400000000001ULL,0x40de984000000002ULL,0x40def0ffffffffffULL,0x40df4a4000000000ULL,
    0x40dfa40000000001ULL,0x40dffe4000000004ULL,0x40e02c8000000001ULL,0x40e05a2000000008ULL,0x40e0880000000001ULL,0x40e0b61ffffffffeULL,
    0x40e0e48000000003ULL,0x40e1132000000004ULL,0x40e1420000000002ULL,0x40e1712000000001ULL,0x40e1a08000000000ULL,0x40e1d02000000000ULL,
    0x40e1ffffffffffffULL,0x40e2302000000002ULL,0x40e2608000000001ULL,0x40e2912000000005ULL,0x40e2c1fffffffffaULL,0x40e2f32000000001ULL,
    0x40e3247fffffffffULL,0x40e3561fffffffffULL,0x40e387fffffffffdULL,0x40e3ba2000000003ULL,0x40e3ec8000000006ULL,0x40e41f2000000002ULL,
    0x40e451fffffffffdULL,0x40e4852000000003ULL,0x40e4b88000000001ULL,0x40e4ec2000000000ULL,0x40e5200000000004ULL,0x40e5541ffffffffeULL,
    0x40e5887ffffffffeULL,0x40e5bd2000000004ULL,0x40e5f20000000004ULL,0x40e6272000000008ULL,0x40e65c7ffffffffcULL,0x40e6921ffffffffaULL,
    0x40e6c80000000005ULL,0x40e6fe2000000002ULL,0x40e7347ffffffffdULL,0x40e76b2000000002ULL,0x40e7a2000000000bULL,0x40e7d92000000001ULL,
    0x40e8108000000002ULL,0x40e8482000000000ULL,0x40e87ffffffffffcULL,0x40e8b82000000003ULL,0x40e8f0800000000aULL,0x40e9292000000009ULL,
    0x40e9620000000005ULL,0x40e99b2000000006ULL,0x40e9d48000000005ULL,0x40ea0e1ffffffffcULL,0x40ea47fffffffffdULL,0x40ea821ffffffffbULL,
    0x40eabc8000000003ULL,0x40eaf72000000005ULL,0x40eb32000000000dULL,0x40eb6d200000000aULL,0x40eba8800000000cULL,0x40ebe4200000000bULL,
    0x40ec200000000002ULL,0x40ec5c2000000003ULL,0x40ec98800000000bULL,0x40ecd52000000004ULL,0x40ed120000000005ULL,0x40ed4f200000000fULL,
    0x40ed8c8000000000ULL,0x40edca2000000002ULL,0x40ee080000000007ULL,0x40ee461ffffffffcULL,0x40ee847fffffffffULL,0x40eec32000000000ULL,
    0x40ef020000000004ULL,0x40ef412000000003ULL,0x40ef808000000006ULL,0x40efc01ffffffffeULL,0x40f0000000000000ULL,0x40f0201000000005ULL,
    0x40f0403fffffffffULL,0x40f0608ffffffffaULL,0x40f080ffffffffffULL,0x40f0a19000000003ULL,0x40f0c23fffffffffULL,0x40f0e30ffffffffeULL,
    0x40f1040000000006ULL,0x40f1251000000005ULL,0x40f1464000000008ULL,0x40f1679000000005ULL,0x40f188fffffffffdULL,0x40f1aa9000000006ULL,
    0x40f1cc4000000006ULL,0x40f1ee1000000007ULL,0x40f210000000000aULL,0x40f2321000000000ULL,0x40f2544000000004ULL,0x40f276900000000bULL,
    0x40f298fffffffffaULL,0x40f2bb9000000004ULL,0x40f2de3ffffffffbULL,0x40f3010ffffffffcULL,0x40f323fffffffff9ULL,0x40f3471000000004ULL,
    0x40f36a4000000001ULL,0x40f38d9000000000ULL,0x40f3b10000000008ULL,0x40f3d49000000006ULL,0x40f3f83ffffffffdULL,0x40f41c100000000cULL,
    0x40f43ffffffffffeULL,0x40f4641000000009ULL,0x40f4884000000000ULL,0x40f4ac9000000007ULL,0x40f4d10000000003ULL,0x40f4f59000000005ULL,
    0x40f51a3ffffffff9ULL,0x40f53f1000000005ULL,0x40f563fffffffffbULL,0x40f5891000000005ULL,0x40f5ae4000000004ULL,0x40f5d3900000000dULL,
    0x40f5f90000000004ULL,0x40f61e8ffffffffcULL,0x40f6443ffffffffdULL,0x40f66a0ffffffff6ULL,0x40f68ffffffffffeULL,0x40f6b60ffffffffeULL,
    0x40f6dc3ffffffffbULL,0x40f7028ffffffff9ULL,0x40f728fffffffff5ULL,0x40f74f9000000000ULL,0x40f7764000000008ULL,0x40f79d1000000007ULL,
    0x40f7c40000000003ULL,0x40f7eb0ffffffffeULL,0x40f8123ffffffff8ULL,0x40f8399000000005ULL,0x40f861000000000aULL,0x40f8889000000003ULL,
    0x40f8b0400000000cULL,0x40f8d80ffffffffeULL,0x40f8fffffffffffaULL,0x40f9280ffffffffbULL,0x40f9504000000007ULL,0x40f9788ffffffffaULL,
    0x40f9a0fffffffffcULL,0x40f9c98ffffffff8ULL,0x40f9f23ffffffffcULL,0x40fa1b1000000004ULL,0x40fa440000000001ULL,0x40fa6d0fffffffffULL,
    0x40fa964000000002ULL,0x40fabf8ffffffffdULL,0x40fae8fffffffff4ULL,0x40fb12900000000bULL,0x40fb3c4000000010ULL,0x40fb661000000009ULL,
    0x40fb8ffffffffffbULL,0x40fbba1000000003ULL,0x40fbe4400000000aULL,0x40fc0e9000000000ULL,0x40fc390000000009ULL,0x40fc639000000007ULL,
    0x40fc8e3ffffffffbULL,0x40fcb90ffffffff3ULL,0x40fce40000000000ULL,0x40fd0f1000000004ULL,0x40fd3a400000000aULL,0x40fd658ffffffffcULL,
    0x40fd910000000006ULL,0x40fdbc9000000008ULL,0x40fde84000000002ULL,0x40fe141000000002ULL,0x40fe3ffffffffff6ULL,0x40fe6c1000000005ULL,
    0x40fe983ffffffff8ULL,0x40fec49000000005ULL,0x40fef10000000009ULL,0x40ff1d8ffffffff6ULL,0x40ff4a4000000000ULL,0x40ff770fffffffffULL,
    0x40ffa4000000000cULL,0x40ffd10ffffffff9ULL,0x40fffe4000000004ULL,0x410015c800000000ULL,0x41002c8000000001ULL,0x41004347fffffffeULL,
    0x41005a2000000002ULL,0x4100710800000003ULL,0x4100880000000007ULL,0x41009f07ffffffffULL,0x4100b62000000004ULL,0x4100cd47fffffffbULL,
    0x4100e47ffffffffdULL,0x4100fbc800000007ULL,0x4101132000000004ULL,0x41012a87ffffffffULL,0x4101420000000002ULL,0x4101598800000007ULL,
    0x4101712000000007ULL,0x410188c800000004ULL,0x4101a08000000006ULL,0x4101b84800000009ULL,0x4101d02000000006ULL,0x4101e80800000000ULL,
    0x4101ffffffffffffULL,0x410218080000000cULL,0x4102302000000008ULL,0x41024847fffffffeULL,0x4102608000000007ULL,0x410278c7fffffff9ULL,
    0x4102911ffffffffeULL,0x4102a98800000006ULL,0x4102c1fffffffffaULL,0x4102da87fffffffeULL,0x4102f32000000008ULL,0x41030bc800000003ULL,
    0x4103248000000005ULL,0x41033d4800000009ULL,0x4103562000000006ULL,0x41036f0800000008ULL,0x4103880000000004ULL,0x4103a10800000009ULL,
    0x4103ba1ffffffffcULL,0x4103d34800000001ULL,0x4103ec8000000006ULL,0x410405c7fffffff8ULL,0x41041f2000000002ULL,0x4104388800000003ULL,
    0x410451fffffffffdULL,0x41046b8800000003ULL,0x410485200000000aULL,0x41049ec800000003ULL,0x4104b88000000001ULL,0x4104d24800000007ULL,
    0x4104ec2000000007ULL,0x4105060800000000ULL,0x4105200000000004ULL,0x41053a0800000008ULL,0x4105542000000006ULL,0x41056e4800000002ULL,
    0x4105888000000006ULL,0x4105a2c7fffffff9ULL,0x4105bd2000000004ULL,0x4105d78800000000ULL,0x4105f1fffffffffcULL,0x41060c8800000002ULL,
    0x4106272000000008ULL,0x410641c800000000ULL,0x41065c7ffffffffcULL,0x41067747fffffffcULL,0x4106921ffffffffaULL,0x4106ad07fffffff7ULL,
    0x4106c8000000000dULL,0x4106e307fffffffcULL,0x4106fe200000000aULL,0x41071947ffffffffULL,0x4107348000000005ULL,0x41074fc800000007ULL,
    0x41076b2000000002ULL,0x41078687ffffffffULL,0x4107a20000000003ULL,0x4107bd8800000008ULL,0x4107d92000000001ULL,0x4107f4c7fffffffcULL,
    0x4108107ffffffffaULL,0x41082c4800000002ULL,0x4108482000000000ULL,0x4108640800000004ULL,0x41087ffffffffffcULL,0x41089c080000000aULL,
    0x4108b82000000003ULL,0x4108d4480000000aULL,0x4108f08000000001ULL,0x41090cc80000000dULL,0x4109292000000009ULL,0x41094587fffffffbULL,
    0x410962000000000eULL,0x41097e8800000005ULL,0x41099b200000000fULL,0x4109b7c80000000cULL,0x4109d48000000005ULL,0x4109f14800000006ULL,
    0x410a0e2000000005ULL,0x410a2b080000000bULL,0x410a480000000006ULL,0x410a6507fffffff6ULL,0x410a821ffffffffbULL,0x410a9f480000000cULL,
    0x410abc8000000003ULL,0x410ad9c7fffffff8ULL,0x410af71ffffffffcULL,0x410b148800000009ULL,0x410b31fffffffffaULL,0x410b4f87fffffff7ULL,
    0x410b6d200000000aULL,0x410b8ac800000003ULL,0x410ba8800000000cULL,0x410bc6480000000cULL,0x410be4200000000bULL,0x410c0207fffffffcULL,
    0x410c20000000000cULL,0x410c3e07ffffffffULL,0x410c5c1ffffffffaULL,0x410c7a47fffffff3ULL,0x410c988000000001ULL,0x410cb6c800000005ULL,
    0x410cd51ffffffffaULL,0x410cf387fffffffaULL,0x410d120000000005ULL,0x410d30880000000fULL,0x410d4f2000000005ULL,0x410d6dc7fffffff8ULL,
    0x410d8c8000000000ULL,0x410dab4800000004ULL,0x410dca2000000002ULL,0x410de90800000001ULL,0x410e080000000011ULL,0x410e270800000008ULL,
    0x410e462000000006ULL,0x410e6547fffffffcULL,0x410e847fffffffffULL,0x410ea3c7fffffffbULL,0x410ec32000000000ULL,0x410ee2880000000fULL,
    0x410f02000000000eULL,0x410f218800000002ULL,0x410f412000000003ULL,0x410f60c80000000aULL,0x410f807ffffffffbULL,0x410fa04800000001ULL,
    0x410fc02000000009ULL,0x410fe00800000000ULL,0x4110000000000000ULL,0x41101003fffffffcULL,0x4110201000000005ULL,0x4110302400000008ULL,
    0x4110403fffffffffULL,0x41105063fffffffcULL,0x4110608ffffffffaULL,0x411070c400000005ULL,0x411080ffffffffffULL,0x4110914400000007ULL,
    0x4110a19000000003ULL,0x4110b1e400000004ULL,0x4110c23fffffffffULL,0x4110d2a400000000ULL,0x4110e3100000000aULL,0x4110f38400000008ULL,
    0x4111040000000006ULL,0x4111148400000002ULL,0x4111251000000005ULL,0x411135a400000007ULL,0x4111464000000008ULL,0x411156e400000004ULL,
    0x4111679000000005ULL,0x4111784400000005ULL,0x411188fffffffffdULL,0x411199c3ffffffffULL,0x4111aa9000000006ULL,0x4111bb6400000001ULL,
    0x4111cc4000000006ULL,0x4111dd2400000004ULL,0x4111ee1000000007ULL,0x4111ff0400000001ULL,0x41120ffffffffffeULL,0x41122103ffffffffULL,
    0x4112321000000000ULL,0x4112432400000006ULL,0x4112544000000004ULL,0x4112656400000001ULL,0x4112768ffffffffeULL,0x411287c400000003ULL,
    0x411298fffffffffaULL,0x4112aa4400000005ULL,0x4112bb9000000004ULL,0x4112cce400000004ULL,0x4112de3ffffffffbULL,0x4112efa3ffffffffULL,
    0x4113010ffffffffcULL,0x4113128400000003ULL,0x4113240000000006ULL,0x4113358400000004ULL,0x4113471000000004ULL,0x411358a400000000ULL,
    0x41136a4000000001ULL,0x41137be40000000aULL,0x41138d9000000000ULL,0x41139f43fffffffaULL,0x4113b10000000008ULL,0x4113c2c3fffffffeULL,
    0x4113d49000000006ULL,0x4113e66400000006ULL,0x4113f83ffffffffdULL,0x41140a2400000006ULL,0x41141c100000000cULL,0x41142e03ffffffffULL,
    0x411440000000000cULL,0x411452040000000bULL,0x4114641000000009ULL,0x4114762400000008ULL,0x4114884000000000ULL,0x41149a6400000002ULL,
    0x4114ac9000000007ULL,0x4114bec400000004ULL,0x4114d10000000003ULL,0x4114e3440000000cULL,0x4114f58ffffffff6ULL,0x411507e3ffffffffULL,
    0x41151a4000000008ULL,0x41152ca3fffffffbULL,0x41153f1000000005ULL,0x4115518400000008ULL,0x411563fffffffffbULL,0x4115768400000000ULL,
    0x4115891000000005ULL,0x41159ba400000004ULL,0x4115ae4000000004ULL,0x4115c0e400000006ULL,0x4115d38ffffffffeULL,0x4115e64400000000ULL,
    0x4115f90000000004ULL,0x41160bc400000006ULL,0x41161e8ffffffffcULL,0x411631640000000aULL,0x4116443ffffffffdULL,0x411657240000000bULL,
    0x41166a1000000006ULL,0x41167d040000000aULL,0x411690000000000dULL,0x4116a30400000001ULL,0x4116b6100000000eULL,0x4116c92400000006ULL,
    0x4116dc3ffffffffbULL,0x4116ef6400000000ULL,0x4117028ffffffff9ULL,0x411715c3fffffffaULL,0x4117290000000005ULL,0x41173c440000000dULL,
    0x41174f9000000000ULL,0x411762e400000008ULL,0x4117764000000008ULL,0x411789a400000007ULL,0x41179d1000000007ULL,0x4117b08400000004ULL,
    0x4117c40000000003ULL,0x4117d783fffffffaULL,0x4117eb0ffffffffeULL,0x4117fea400000005ULL,0x4118124000000009ULL,0x411825e400000009ULL,
    0x4118399000000005ULL,0x41184d4400000004ULL,0x411861000000000aULL,0x411874c400000003ULL,0x4118889000000003ULL,0x41189c6400000008ULL,
    0x4118b0400000000cULL,0x4118c423fffffffdULL,0x4118d80ffffffffeULL,0x4118ec0400000008ULL,0x4118fffffffffffaULL,0x4119140400000005ULL,
    0x4119280ffffffffbULL,0x41193c23ffffffffULL,0x4119504000000007ULL,0x411964640000000aULL,0x4119788ffffffffaULL,0x41198cc400000002ULL,
    0x4119a0fffffffffcULL,0x4119b54400000004ULL,0x4119c9900000000aULL,0x4119dde3fffffff8ULL,0x4119f2400000000eULL,0x411a06a400000008ULL,
    0x411a1b1000000004ULL,0x411a2f83fffffff8ULL,0x411a440000000001ULL,0x411a588400000002ULL,0x411a6d0fffffffffULL,0x411a81a3fffffffcULL,
    0x411a964000000002ULL,0x411aaae3fffffff6ULL,0x411abf8ffffffffdULL,0x411ad44400000001ULL,0x411ae90000000007ULL,0x411afdc400000005ULL,
    0x411b12900000000bULL,0x411b2763ffffffffULL,0x411b3c3ffffffffdULL,0x411b512400000012ULL,0x411b661000000009ULL,0x411b7b040000000eULL,
    0x411b8ffffffffffbULL,0x411ba503fffffffcULL,0x411bba1000000003ULL,0x411bcf2400000003ULL,0x411be4400000000aULL,0x411bf963fffffffeULL,
    0x411c0e9000000000ULL,0x411c23c400000007ULL,0x411c38fffffffff6ULL,0x411c4e43fffffff5ULL,0x411c639000000007ULL,0x411c78e40000000eULL,
    0x411c8e3ffffffffbULL,0x411ca3a3ffffffffULL,0x411cb91000000007ULL,0x411cce83fffffffbULL,0x411ce40000000000ULL,0x411cf98400000001ULL,
    0x411d0f1000000004ULL,0x411d24a400000002ULL,0x411d3a3ffffffff5ULL,0x411d4fe400000004ULL,0x411d659000000011ULL,0x411d7b4400000005ULL,
    0x411d910000000006ULL,0x411da6c3fffffffdULL,0x411dbc9000000008ULL,0x411dd263fffffffaULL,0x411de84000000002ULL,0x411dfe2400000003ULL,
    0x411e141000000002ULL,0x411e2a040000000bULL,0x411e3ffffffffff6ULL,0x411e56040000000fULL,0x411e6c1000000005ULL,0x411e822400000005ULL,
    0x411e983ffffffff8ULL,0x411eae6400000002ULL,0x411ec49000000005ULL,0x411edac3fffffff5ULL,0x411ef10000000009ULL,0x411f074400000009ULL,
    0x411f1d8ffffffff6ULL,0x411f33e40000000aULL,0x411f4a4000000000ULL,0x411f60a3fffffff6ULL,0x411f770fffffffffULL,0x411f8d840000000dULL,
    0x411fa4000000000cULL,0x411fba8400000013ULL,0x411fd10ffffffff9ULL,0x411fe7a40000000eULL,0x411ffe4000000004ULL,0x41200a71fffffffcULL,
    0x412015c800000000ULL,0x41202121ffffffffULL,0x41202c8000000001ULL,0x412037e200000007ULL,0x41204347fffffffeULL,0x41204eb1fffffffeULL,
    0x41205a2000000002ULL,0x41206591fffffffbULL,0x4120710800000003ULL,0x41207c8200000002ULL,0x4120880000000007ULL,0x4120938200000004ULL,
    0x41209f07ffffffffULL,0x4120aa91ffffffffULL,0x4120b62000000004ULL,0x4120c1b200000001ULL,0x4120cd4800000006ULL,0x4120d8e200000006ULL,
    0x4120e47ffffffffdULL,0x4120f021ffffffffULL,0x4120fbc7fffffffcULL,0x4121077200000003ULL,0x4121132000000004ULL,0x41211ed1fffffffaULL,
    0x41212a87ffffffffULL,0x4121364200000002ULL,0x4121420000000002ULL,0x41214dc1ffffffffULL,0x4121598800000007ULL,0x4121655200000006ULL,
    0x4121712000000007ULL,0x41217cf1fffffff9ULL,0x412188c800000004ULL,0x412194a200000001ULL,0x4121a08000000006ULL,0x4121ac6200000001ULL,
    0x4121b84800000009ULL,0x4121c43200000001ULL,0x4121d02000000006ULL,0x4121dc1200000004ULL,0x4121e80800000000ULL,0x4121f401ffffffffULL,
    0x4121ffffffffffffULL,0x41220c0200000002ULL,0x4122180800000000ULL,0x4122241200000005ULL,0x4122302000000008ULL,0x41223c3200000006ULL,
    0x412248480000000bULL,0x4122546200000002ULL,0x4122608000000007ULL,0x41226ca200000005ULL,0x412278c7fffffff9ULL,0x412284f1ffffffffULL,
    0x4122911ffffffffeULL,0x41229d5200000002ULL,0x4122a98800000006ULL,0x4122b5c200000002ULL,0x4122c1fffffffffaULL,0x4122ce4200000002ULL,
    0x4122da87fffffffeULL,0x4122e6d200000004ULL,0x4122f32000000008ULL,0x4122ff71fffffffdULL,0x41230bc800000003ULL,0x412318220000000bULL,
    0x4123248000000005ULL,0x412330e1fffffff9ULL,0x41233d4800000009ULL,0x412349b200000005ULL,0x4123562000000006ULL,0x4123629200000002ULL,
    0x41236f0800000008ULL,0x41237b81ffffffffULL,0x4123880000000004ULL,0x4123948200000004ULL,0x4123a10800000009ULL,0x4123ad91fffffffcULL,
    0x4123ba200000000aULL,0x4123c6b200000001ULL,0x4123d34800000001ULL,0x4123dfe200000006ULL,0x4123ec7ffffffff8ULL,0x4123f921fffffffeULL,
    0x412405c800000006ULL,0x4124127200000001ULL,0x41241f2000000002ULL,0x41242bd1fffffff9ULL,0x4124388800000003ULL,0x4124454200000006ULL,
    0x412451fffffffffdULL,0x41245ec20000000cULL,0x41246b8800000003ULL,0x412478520000000dULL,0x4124851ffffffffcULL,0x412491f200000003ULL,
    0x41249ec800000003ULL,0x4124aba200000002ULL,0x4124b88000000001ULL,0x4124c561fffffffdULL,0x4124d247fffffff8ULL,0x4124df3200000007ULL,
    0x4124ec2000000007ULL,0x4124f91200000000ULL,0x4125060800000000ULL,0x4125130200000003ULL,0x4125200000000004ULL,0x41252d0200000006ULL,
    0x41253a0800000008ULL,0x41254711fffffff8ULL,0x4125542000000006ULL,0x412561320000000aULL,0x41256e4800000002ULL,0x41257b6200000005ULL,
    0x4125888000000006ULL,0x412595a20000000bULL,0x4125a2c800000008ULL,0x4125aff200000003ULL,0x4125bd2000000004ULL,0x4125ca5200000003ULL,
    0x4125d78800000000ULL,0x4125e4c20000000dULL,0x4125f1fffffffffcULL,0x4125ff420000000eULL,0x41260c8800000002ULL,0x412619d200000004ULL,
    0x4126271ffffffff9ULL,0x4126347200000005ULL,0x412641c800000000ULL,0x41264f2200000006ULL,0x41265c7ffffffffcULL,0x412669e200000002ULL,
    0x412677480000000bULL,0x412684b1fffffffaULL,0x4126921ffffffffaULL,0x41269f91fffffffdULL,0x4126ad07fffffff7ULL,0x4126ba8200000004ULL,
    0x4126c7fffffffffdULL,0x4126d58200000002ULL,0x4126e307fffffffcULL,0x4126f091fffffff9ULL,0x4126fe200000000aULL,0x41270bb200000002ULL,
    0x41271947ffffffffULL,0x412726e200000001ULL,0x4127348000000005ULL,0x4127422200000007ULL,0x41274fc800000007ULL,0x41275d71fffffffcULL,
    0x41276b2000000002ULL,0x412778d200000008ULL,0x41278687ffffffffULL,0x4127944200000004ULL,0x4127a20000000003ULL,0x4127afc200000007ULL,
    0x4127bd8800000008ULL,0x4127cb51fffffffcULL,0x4127d92000000001ULL,0x4127e6f200000005ULL,0x4127f4c7fffffffcULL,0x412802a1fffffffeULL,
    0x412810800000000aULL,0x41281e620000000aULL,0x41282c4800000002ULL,0x41283a3200000005ULL,0x4128482000000000ULL,0x4128561200000000ULL,
    0x4128640800000004ULL,0x412872020000000bULL,0x41287ffffffffffcULL,0x41288e01fffffffdULL,0x41289c080000000aULL,0x4128aa1200000003ULL,
    0x4128b82000000003ULL,0x4128c631fffffff9ULL,0x4128d4480000000aULL,0x4128e261fffffffbULL,0x4128f08000000001ULL,0x4128fea1fffffffdULL,
    0x41290cc80000000dULL,0x41291af200000001ULL,0x4129292000000009ULL,0x4129375200000006ULL,0x41294587fffffffbULL,0x412953c200000005ULL,
    0x412961fffffffffcULL,0x41297041fffffffeULL,0x41297e8800000005ULL,0x41298cd1fffffffdULL,0x41299b1ffffffffdULL,0x4129a971fffffffbULL,
    0x4129b7c80000000cULL,0x4129c62200000007ULL,0x4129d48000000005ULL,0x4129e2e200000009ULL,0x4129f14800000006ULL,0x4129ffb1fffffffdULL,
    0x412a0e2000000005ULL,0x412a1c9200000000ULL,0x412a2b080000000bULL,0x412a3981ffffffffULL,0x412a480000000006ULL,0x412a568200000003ULL,
    0x412a6507fffffff6ULL,0x412a739200000008ULL,0x412a821ffffffffbULL,0x412a90b200000006ULL,0x412a9f480000000cULL,0x412aade200000000ULL,
    0x412abc8000000003ULL,0x412acb21fffffffcULL,0x412ad9c80000000bULL,0x412ae871fffffffdULL,0x412af7200000000fULL,0x412b05d1fffffffbULL,
    0x412b148800000009ULL,0x412b23420000000cULL,0x412b31fffffffffaULL,0x412b40c200000005ULL,0x412b4f87fffffff7ULL,0x412b5e51fffffffeULL,
    0x412b6d1ffffffff7ULL,0x412b7bf200000009ULL,0x412b8ac800000003ULL,0x412b99a200000002ULL,0x412ba87ffffffff9ULL,0x412bb761fffffff8ULL,
    0x412bc6480000000cULL,0x412bd53200000003ULL,0x412be41ffffffff8ULL,0x412bf311fffffffdULL,0x412c0207fffffffcULL,0x412c110200000002ULL,
    0x412c20000000000cULL,0x412c2f020000000dULL,0x412c3e07ffffffffULL,0x412c4d120000000cULL,0x412c5c1ffffffffaULL,0x412c6b3200000005ULL,
    0x412c7a4800000007ULL,0x412c896200000002ULL,0x412c988000000001ULL,0x412ca7a20000000cULL,0x412cb6c800000005ULL,0x412cc5f20000000cULL,
    0x412cd51ffffffffaULL,0x412ce45200000008ULL,0x412cf387fffffffaULL,0x412d02c20000000aULL,0x412d120000000005ULL,0x412d2141fffffff8ULL,
    0x412d30880000000fULL,0x412d3fd1ffffffffULL,0x412d4f2000000005ULL,0x412d5e7200000004ULL,0x412d6dc7fffffff8ULL,0x412d7d2200000000ULL,
    0x412d8c8000000000ULL,0x412d9be200000005ULL,0x412dab4800000004ULL,0x412dbab200000012ULL,0x412dca2000000002ULL,0x412dd9920000000cULL,
    0x412de90800000001ULL,0x412df88200000010ULL,0x412e07fffffffffdULL,0x412e178200000011ULL,0x412e270800000008ULL,0x412e369200000002ULL,
    0x412e462000000006ULL,0x412e55b1ffffffffULL,0x412e654800000011ULL,0x412e74e20000000bULL,0x412e847fffffffffULL,0x412e9421fffffff7ULL,
    0x412ea3c7fffffffbULL,0x412eb3720000000bULL,0x412ec32000000000ULL,0x412ed2d200000008ULL,0x412ee2880000000fULL,0x412ef2420000000dULL,
    0x412f02000000000eULL,0x412f11c200000007ULL,0x412f218800000002ULL,0x412f315200000002ULL,0x412f412000000003ULL,0x412f50f20000000bULL,
    0x412f60c80000000aULL,0x412f70a1fffffffcULL,0x412f808000000011ULL,0x412f9061ffffffffULL,0x412fa04800000001ULL,0x412fb03200000002ULL,
    0x412fc02000000009ULL,0x412fd01200000002ULL,0x412fe00800000000ULL,0x412ff00200000007ULL,0x4130000000000000ULL,
};
struct Run {ClawPlayerFadeContext* c;ClawPlayerFadeDependency d;void* u;uint32_t reads=0;};
int32_t si(uint32_t x){int32_t y;std::memcpy(&y,&x,4);return y;}
uint32_t* span(Run& r,uint32_t t,uint32_t n){auto* p=r.c->scene.lookup?r.c->scene.lookup(r.c->scene.context,t,n):nullptr;if(!p)r.c->fault=1;return p;}
uint32_t rd(Run& r,uint32_t t){auto* p=span(r,t,1);return p?*p:0;}
void wr(Run& r,uint32_t t,uint32_t v){auto* p=span(r,t,1);if(p)*p=v;}
uint8_t* bytes(Run& r,uint32_t t,uint32_t n){if(!n)return nullptr;auto* p=span(r,t&~3u,(n+(t&3u)+3u)/4u);return p?reinterpret_cast<uint8_t*>(p)+(t&3u):nullptr;}
uint32_t svc(Run& r,uint32_t f,uint32_t receiver,std::initializer_list<uint32_t> a={}){ClawPlayerFadeCall e{};e.function=f;e.receiver=receiver;e.argumentCount=uint32_t(a.size());std::copy(a.begin(),a.end(),e.arguments);if(r.d)return r.d(r.c,&e,r.u);if(e.argumentCount<=4&&r.c->scene.call){ClawSceneActorCall s{};s.function=f;s.receiver=receiver;s.argumentCount=e.argumentCount;std::copy_n(e.arguments,e.argumentCount,s.arguments);return r.c->scene.call(r.c->scene.context,s);}r.c->fault=1;return 0;}
uint32_t clock(Run& r,uint32_t f){const uint32_t maximum=r.c->maximumClockReads?r.c->maximumClockReads:1000000;if(++r.reads>maximum){r.c->fault=2;return 0;}return svc(r,f,0);}
uint32_t ftol(double v){if(!std::isfinite(v)||v>=9223372036854775808.0||v< -9223372036854775808.0)return 0;return uint32_t(uint64_t(int64_t(v)));}
uint32_t execute(Run&,uint32_t,uint32_t,const uint32_t*,uint32_t);
uint32_t invoke(Run& r,uint32_t f,uint32_t t,std::initializer_list<uint32_t> a={}){uint32_t args[6]{};std::copy(a.begin(),a.end(),args);return execute(r,f,t,args,uint32_t(a.size()));}
uint32_t virt(Run& r,uint32_t t,uint32_t slot,std::initializer_list<uint32_t> a={}){const uint32_t f=rd(r,rd(r,t)+slot);if(r.c->fault)return 0;return invoke(r,f,t,a);}
void wait(Run& r,uint32_t duration,uint32_t slot){const uint32_t end=clock(r,slot)+duration;uint32_t now=clock(r,slot);while(!r.c->fault&&now<end)now=clock(r,slot);}
void zero(Run& r,uint32_t t,uint32_t n){if(si(n)<=0)return;auto* p=bytes(r,t,n);if(p)std::memset(p,0,n);}
void forward(Run& r,uint32_t dst,uint32_t src,uint32_t n){if(si(n)<=0)return;auto* a=bytes(r,dst,n);auto* b=bytes(r,src,n);if(a&&b)for(uint32_t i=0;i<n;++i)a[i]=b[i];}
void unlock(Run& r,uint32_t surface){if(!surface||r.c->fault)return;const uint32_t dd=rd(r,surface+8),f=rd(r,rd(r,dd)+0x80);if(!r.c->fault)svc(r,f,0,{dd,0});}
uint32_t arrayDependency(ClawCArrayContext*,const ClawCArrayCall* c,void* user){auto& r=*static_cast<Run*>(user);ClawPlayerFadeCall e{};e.function=c->function;e.receiver=c->receiver;e.argumentCount=c->argumentCount;std::copy_n(c->arguments,c->argumentCount,e.arguments);if(r.d)return r.d(r.c,&e,r.u);return svc(r,e.function,e.receiver,{e.arguments[0]});}
void resize(Run& r,uint32_t t,uint32_t size){ClawCArrayContext c{};c.scene=r.c->scene;claw_carray_defaults(&c);uint32_t result=0;claw_carray_entry(0x4f5915,t,size,0xffffffff,0,&c,arrayDependency,&r,&result);if(c.fault)r.c->fault=c.fault;}
uint32_t primary(Run& r,uint32_t owner){return rd(r,rd(r,rd(r,rd(r,owner+0xc)+4)+0x10)+0x2c);}
uint32_t execute(Run& r,uint32_t fn,uint32_t t,const uint32_t* a,uint32_t n){
 if(r.c->fault)return 0;
 auto need=[&](uint32_t count){if(n<count){r.c->fault=2;return false;}return true;};
 switch(fn){
 case 0x4ecb30:wr(r,t,0);return t;
 case 0x4ecbc0:{auto* p=span(r,t,9);if(!p)return 0;p[0]=2;p[1]=p[2]=p[5]=p[8]=0;p[4]=1;p[6]=320;p[7]=240;return t;}
 case 0x4ebf80:{auto* p=span(r,t,9);if(!p)return 0;p[4]=0x5141c0;p[5]=p[6]=p[7]=p[8]=p[2]=p[3]=0;return t;}
 case 0x4c61d0:{auto* p=span(r,t,6);if(!p)return 0;p[0]=p[2]=p[3]=p[4]=p[5]=0;p[1]=0x5136e8;return t;}
 case 0x4ec8d0:invoke(r,0x4c61d0,t+4);wr(r,t,0x5141d8);wr(r,t+0x1c,0);wr(r,t+0x30,1);return t;
 case 0x4ed5e0:invoke(r,0x4ec8d0,t);wr(r,t,0x514250);wr(r,t+0x40,0);return t;
 case 0x4ecb00:if(need(2)){wr(r,t+0x24,a[0]);wr(r,t+0x28,a[1]);}return 0;
 case 0x4ecb20:if(need(1))wr(r,t+0x2c,a[0]);return 0;
 case 0x4ed670:{if(!need(1))return 0;auto* d=span(r,a[0],9);if(!d)return 0;wr(r,t+0x20,0);wr(r,t+0x38,d[1]?d[1]:rd(r,t+0x24));wr(r,t+0x3c,d[2]?d[2]:rd(r,t+0x28));wr(r,t+0x48,d[4]);wr(r,t+0x4c,d[6]);wr(r,t+0x50,d[7]);wr(r,t+0x44,d[3]);wr(r,t+0x2060,d[5]);if(si(d[5])>0&&!d[8]&&!d[3])return 0;uint32_t s=rd(r,t+0x38);if(!s||(!rd(r,t+0x3c)&&!rd(r,t+0x48)))return 0;uint32_t w=rd(r,s+0x18),h=rd(r,s+0x14);wr(r,t+0x2064,w);wr(r,t+0x2068,h);if(si(d[6])<0||si(d[7])<0||si(d[6])>=si(w)||si(d[7])>=si(h))return 0;if(si(h)>1024){r.c->fault=2;return 0;}for(int32_t y=0;y<si(rd(r,t+0x2068));++y){wr(r,t+0x60+uint32_t(y)*4,rd(r,t+0x48)?0:rd(r,t+0x4c));wr(r,t+0x1060+uint32_t(y)*4,rd(r,t+0x48)?rd(r,t+0x2064):rd(r,t+0x4c));}if(si(rd(r,t+0x2060))>0){if(d[8])wr(r,t+0x1c,d[8]);else{uint32_t p=svc(r,0x4c6bd0,t+4,{rd(r,rd(r,t+0x44)+0xc),rd(r,t+0x2060),0});wr(r,t+0x1c,p);wr(r,t+0x30,1);}}return 1;}
 case 0x4ee6b0:{const uint32_t x=rd(r,t+0x4c),y=rd(r,t+0x50),surface=rd(r,t+0x38),w=rd(r,surface+0x18),h=rd(r,surface+0x14);const uint32_t xs[4]={x,y,h-y,w-x};double q[4]{};for(unsigned i=0;i<4;++i){if(xs[i]>1024){r.c->fault=2;return 0;}std::memcpy(&q[i],&squareBits[xs[i]],8);}double maximum=std::sqrt(q[0]+q[1]);maximum=std::max(maximum,std::sqrt(q[0]+q[2]));maximum=std::max(maximum,std::sqrt(q[3]+q[1]));maximum=std::max(maximum,std::sqrt(q[3]+q[2]));uint32_t value=ftol(maximum);wr(r,t+0x5c,value);return value;}
 case 0x4ee820:if(si(rd(r,t+0x2060))>0&&rd(r,t+0x48)){const uint32_t capture=svc(r,0x4bc960,rd(r,t+0x2c),{rd(r,t+0x2064),rd(r,t+0x2068),0,0,0xffffffff});wr(r,t+0x40,capture);svc(r,0x4b9c50,capture,{rd(r,t+0x38)});}return 0;
 case 0x4ee860:{const uint32_t capture=rd(r,t+0x40);if(capture){svc(r,0x4bc4f0,rd(r,t+0x2c),{capture});wr(r,t+0x40,0);}return 0;}
 case 0x4ee170:if(si(rd(r,t+0x2060))>0)r.c->fault=3;return 0;
 case 0x4ed800:{if(!need(1))return 0;const uint32_t step=a[0],delta=step-rd(r,t+0x20);uint32_t s=rd(r,t+0x38);if(s)wr(r,t+0x54,svc(r,0x4b9730,s,{0}));s=rd(r,t+0x3c);if(s)wr(r,t+0x58,svc(r,0x4b9730,s,{0}));uint32_t bpp=rd(r,rd(r,t+0x38)+0xac);if(rd(r,t+0x1c))rd(r,rd(r,t+0x1c)+8);const bool clear=rd(r,t+0x48)!=0;if(clear&&rd(r,t+0x40))svc(r,0x4b9730,rd(r,t+0x40),{0});if(si(rd(r,t+0x2060))>0){r.c->fault=3;return 0;}if(si(bpp)<=0||bpp>4){r.c->fault=2;return 0;}const uint32_t radius=clear?rd(r,t+0x5c)-step:step;const int32_t cy=si(rd(r,t+0x50));uint32_t row=uint32_t(std::max(0,si(uint32_t(cy)-radius-delta-rd(r,t+0x2060)*(clear?0u:1u))));uint32_t square=radius*radius;
 for(uint32_t iterations=0;!r.c->fault&&si(row)<std::min(si(rd(r,t+0x2068)),si(delta+radius+uint32_t(cy)+rd(r,t+0x2060)*(clear?0u:1u)));++row){if(++iterations>1024||row>=1024){r.c->fault=2;break;}const uint32_t dstBase=rd(r,t+0x54),srcBase=rd(r,t+0x58),dstPitch=rd(r,rd(r,t+0x38)+0x1c),width=rd(r,t+0x2064);const uint32_t leftToken=t+0x60+row*4,rightToken=t+0x1060+row*4;if(clear&&(si(row)<si(uint32_t(cy)-radius+1)||si(row)>si(uint32_t(cy)+radius-1))){zero(r,dstBase+row*dstPitch,width);continue;}if(!clear&&(si(row)<=si(uint32_t(cy)-radius)||si(row)>=si(uint32_t(cy)+radius)))continue;const uint32_t dy=row-uint32_t(cy);const uint32_t root=ftol(std::sqrt(double(si(square-dy*dy))));const uint32_t cx=rd(r,t+0x4c);const uint32_t right=uint32_t(std::min(si(width),std::max(0,si(cx+root))));const uint32_t left=uint32_t(std::min(si(width),std::max(0,si(cx-root+(clear?1u:0xffffffffu)))));const uint32_t oldLeft=rd(r,leftToken),oldRight=rd(r,rightToken);if(clear){zero(r,dstBase+row*dstPitch+oldLeft*bpp,(left-oldLeft)*bpp);zero(r,dstBase+row*dstPitch+right*bpp,(oldRight-right)*bpp);}else{const uint32_t srcPitch=rd(r,rd(r,t+0x3c)+0x1c);forward(r,dstBase+row*dstPitch+left*bpp,srcBase+row*srcPitch+left*bpp,(oldLeft-left)*bpp);forward(r,dstBase+row*dstPitch+oldRight*bpp,srcBase+row*srcPitch+oldRight*bpp,(right-oldRight)*bpp);}wr(r,leftToken,left);wr(r,rightToken,right);}
 if(clear)unlock(r,rd(r,t+0x40));wr(r,t+0x20,step);unlock(r,rd(r,t+0x38));unlock(r,rd(r,t+0x3c));return 0;}
 case 0x4ec990:if(need(1))wait(r,a[0],0x546a24);return 0;
 case 0x4b8960:if(need(1))wait(r,a[0],0x546df0);return 0;
 case 0x4ec9c0:{if(!need(3))return 0;const uint32_t max=virt(r,t,8);if(si(max)<1||r.c->fault)return 0;virt(r,t,0xc);virt(r,t,4,{0});wait(r,a[1],0x546a24);const uint32_t start=clock(r,0x546a24);const double startFloat=float(start),duration=float(a[0]),maxFloat=float(si(max));uint32_t previous=0,step=0,count=0;do{const uint32_t now=clock(r,0x546a24);step=ftol(((double(now)-startFloat)/duration)*maxFloat);if(previous!=step&&si(step)<=si(max)&&si(step)>0){if(a[2]&&rd(r,t+0x2c)){const uint32_t dd=rd(r,rd(r,t+0x2c)),fn2=rd(r,rd(r,dd)+0x58);svc(r,fn2,0,{dd,1,0});}virt(r,t,4,{step});++count;}previous=step;}while(!r.c->fault&&si(step)<=si(max));if(r.c->fault)return 0;if(step!=max){virt(r,t,4,{max});++count;}const double frames=float(si(count));const uint32_t elapsed=clock(r,0x546a24)-start;const float factor=0.001000000047497451305389404296875f;wr(r,t+0x34,ftol(frames/(double(elapsed)*double(factor))));virt(r,t,0x10);return 0;}
 case 0x42d420:case 0x42d440:if(rd(r,t+0x50)&&rd(r,t+0x14)){if(fn==0x42d420)svc(r,0x4b55a0,rd(r,t+0x50));else svc(r,0x4b55b0,rd(r,t+0x50),{0});}return 0;
 case 0x4ec920:wr(r,t,0x5141d8);if(rd(r,t+0x1c)&&rd(r,t+0x30)){svc(r,0x4c7510,t+4,{rd(r,t+0x1c)});wr(r,t+0x1c,0);}svc(r,0x4c61f0,t+4);return 0;
 case 0x4ed620:wr(r,t,0x514250);return invoke(r,0x4ec920,t);
 case 0x4ed600:if(!need(1))return 0;invoke(r,0x4ed620,t);if(a[0]&1)svc(r,0x4f6428,0,{t});return t;
 case 0x4ec600:{if(!need(1))return 0;uint32_t index=0;while(si(index)<si(rd(r,t+0x18))){if(rd(r,rd(r,t+0x14)+index*4)==a[0])break;if(++index>1000000){r.c->fault=2;return 0;}}if(si(index)>=si(rd(r,t+0x18)))return 0;for(uint32_t j=index;j<rd(r,t+0x18)-1;++j)wr(r,rd(r,t+0x14)+j*4,rd(r,rd(r,t+0x14)+(j+1)*4));wr(r,t+0x18,rd(r,t+0x18)-1);if(a[0])virt(r,a[0],0,{1});return 0;}
 case 0x4ec050:{if(!need(2))return 0;if(a[0]!=1){r.c->fault=3;return 0;}uint32_t descriptor=a[1];if(!descriptor){descriptor=r.c->temporaryDescriptorToken;wr(r,descriptor+12,r.c->descriptorWord3);invoke(r,0x4ecbc0,descriptor);}if(rd(r,descriptor)!=2){r.c->fault=3;return 0;}const uint32_t effect=svc(r,0x4f63ec,0,{0x206c});if(effect)invoke(r,0x4ed5e0,effect);invoke(r,0x4ecb00,effect,{rd(r,t),rd(r,t+4)});invoke(r,0x4ecb20,effect,{rd(r,t+0x24)});if(r.c->fault)return 0;if(!invoke(r,0x4ed670,effect,{descriptor})){r.c->fault=3;return 0;}const uint32_t index=rd(r,t+0x18);resize(r,t+0x10,index+1);wr(r,rd(r,t+0x14)+index*4,effect);return effect;}
 case 0x48fae0:case 0x48fbe0:{if(!need(4))return 0;const uint32_t manager=rd(r,t+0x10);if(!manager)return 0;if(!rd(r,rd(r,t+0xc)+0x1c))return 0;const uint32_t surface=primary(r,t);if(!surface||r.c->fault)return 0;uint32_t other=0;if(fn==0x48fbe0){other=rd(r,rd(r,rd(r,rd(r,t+0xc)+4)+0x14)+0x2c);if(!other||r.c->fault)return 0;} const uint32_t descriptor=r.c->temporaryDescriptorToken;auto* d=span(r,descriptor,9);if(!d)return 0;d[3]=r.c->descriptorWord3;invoke(r,0x4ecbc0,descriptor);d[1]=surface;d[2]=other;d[4]=fn==0x48fae0?1u:0u;d[6]=a[0];d[7]=a[1];const uint32_t effect=invoke(r,0x4ec050,manager,{1,descriptor});if(!effect||r.c->fault)return 0;invoke(r,0x42d420,rd(r,t+4));if(!r.c->globals){r.c->fault=1;return 0;}if(r.c->globals->bypass){wait(r,a[2],0x546df0);if(fn==0x48fae0)svc(r,0x4b97c0,primary(r,t),{0});else svc(r,0x4b9c50,primary(r,t),{other});}else invoke(r,0x4ec9c0,effect,{a[2],a[3],0});if(r.c->fault)return 0;invoke(r,0x42d440,rd(r,t+4));invoke(r,0x4ec600,manager,{effect});return 1;}

 default:{ClawPlayerFadeCall e{};e.function=fn;e.receiver=t;e.argumentCount=n;std::copy_n(a,n,e.arguments);if(r.d)return r.d(r.c,&e,r.u);r.c->fault=1;return 0;}
 }
}
}
uint32_t claw_player_fade_entry(uint32_t fn,uint32_t receiver,const uint32_t* args,uint32_t count,ClawPlayerFadeContext* c,ClawPlayerFadeDependency d,void* user,uint32_t* result){if(!c||count>6||(!args&&count))return 0;switch(fn){case 0x48fae0:case 0x48fbe0:case 0x4ebf80:case 0x4ecbc0:case 0x4ecb30:case 0x4ec050:case 0x4c61d0:case 0x4ec8d0:case 0x4ed5e0:case 0x4ecb00:case 0x4ecb20:case 0x4ed670:case 0x4ee6b0:case 0x4ee820:case 0x4ee860:case 0x4ed800:case 0x4ee170:case 0x4ec9c0:case 0x4ec990:case 0x4b8960:case 0x42d420:case 0x42d440:case 0x4ec600:case 0x4ed600:case 0x4ed620:case 0x4ec920:break;default:return 0;}Run r{c,d,user};const uint32_t v=execute(r,fn,receiver,args,count);if(result)*result=v;return c->fault?0:1;}
