"""Generate source-matched exact-size Story replays from the pinned original."""
import booty_story_helpers as h
for level in range(1,15):
 h.fresh(level);h.realResources();h.realCreation();h.realFrame();h.capture=True;h.compare(0x40b860,('asan init',level),(h.APP,level,3));h.compare(0x40bd60,('asan firstframe',level));h.capture=False
 for i in range(210):
  h.clockNow=(i+1)*100;h.put(0x53720c,[100]);h.capture=i in(49,51,99,149,209);h.compare(0x40bd60,('asan tick',level,i))
 h.capture=True;h.realCleanup();h.compare(0x40bc80,('asan cleanup',level),meaningful=False);h.capture=False
 h.fresh(level);h.realResources();h.realCreation();h.compare(0x40b860,('asan palette init',level),(h.APP,level,3));h.realPalette(level);h.capture=True;h.compare(0x40bca0,('asan enter',level),(3,));h.compare(0x40bed0,('asan restore',level));h.capture=False
h.saveCorpus();print('CAPTURED',len(h.corpus),'whole-source paired exact-size cases',flush=True)
