#!/usr/bin/env python3
"""Run the bounded common-entry cases within the shared Soldier composition."""
import soldier_helpers as h
for fn in(0x43ed70,0x43efe0,0x43fe00,0x43f500,0x404e00,0x404e10,0x44de30,0x440c70,0x440b20,0x440c90,0x44dbb0,0x43fa10):
 s,c=h.fresh();h.policy=h.mutate=0;h.resource_mode=1;h.clear_path=0;h.random_results=[0];h.compare(s,c,fn,('common-smoke',hex(fn)),500,directCommon=fn not in(0x44de30,0x44dbb0))
print('CommonEnemyEntries:',h.calls,'whole original calls;',h.event_count,'ordered complete snapshots.')
