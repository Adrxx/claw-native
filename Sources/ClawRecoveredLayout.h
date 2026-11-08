#ifndef CLAW_RECOVERED_LAYOUT_H
#define CLAW_RECOVERED_LAYOUT_H

#include "ClawRecoveredNames.h"
#include <cstddef>
#include <type_traits>

namespace claw {
namespace recovered {
namespace v10 {

// These are byte-layout contracts, not native overlays on guest storage. Their
// sizes describe only the observed prefixes, not complete allocation sizes.
// Guest memory continues to be accessed through Run at the original token.
struct ActorPrefixLayout {
    uint8_t unknown_before_0x6c[0x6c];
    LogicHolderToken logicHolder;
};

struct LogicHolderPrefixLayout {
    uint8_t unknown_before_0x18[0x18];
    LogicToken logic;
    uint32_t state;
};

struct ActorContextPrefixLayout {
    ActorToken actor;
    ActorToken actorAlias;
    LogicHolderToken logicHolder;
};

static_assert(sizeof(ActorToken) == 4 && alignof(ActorToken) == 4,
              "v1.0 tokens remain 32-bit words");
static_assert(std::is_standard_layout<ActorPrefixLayout>::value, "layout contract");
static_assert(sizeof(ActorPrefixLayout) == 0x70 && alignof(ActorPrefixLayout) == 4,
              "v1.0 actor prefix");
static_assert(offsetof(ActorPrefixLayout, logicHolder) == 0x6c, "0x40e6ab / 0x40f76b");
static_assert(std::is_standard_layout<LogicHolderPrefixLayout>::value, "layout contract");
static_assert(sizeof(LogicHolderPrefixLayout) == 0x20 && alignof(LogicHolderPrefixLayout) == 4,
              "v1.0 logic-holder prefix");
static_assert(offsetof(LogicHolderPrefixLayout, logic) == 0x18, "0x40e702");
static_assert(offsetof(LogicHolderPrefixLayout, state) == 0x1c, "0x40e6ae");
static_assert(std::is_standard_layout<ActorContextPrefixLayout>::value, "layout contract");
static_assert(sizeof(ActorContextPrefixLayout) == 0x0c && alignof(ActorContextPrefixLayout) == 4,
              "v1.0 actor-context prefix");
static_assert(offsetof(ActorContextPrefixLayout, actor) == 0, "0x40f766");
static_assert(offsetof(ActorContextPrefixLayout, actorAlias) == 4, "0x40f768");
static_assert(offsetof(ActorContextPrefixLayout, logicHolder) == 8, "0x40f76e");

// A view is only the original actor token. It neither dereferences memory nor
// materializes a C++ ActorPrefixLayout in the guest heap. Conversion preserves
// the existing Run access expressions and their literal mutation offsets.
class ActorView {
  public:
    explicit constexpr ActorView(ActorToken token) : token_(token) {}
    constexpr operator ActorToken() const { return token_; }

  private:
    ActorToken token_;
};

static_assert(std::is_standard_layout<ActorView>::value, "token-only view");
static_assert(sizeof(ActorView) == sizeof(ActorToken) && alignof(ActorView) == alignof(ActorToken),
              "an actor view contains only a guest token");

// Access is always through the supplied guest-memory transport. The optional
// byte delta lets the opt-in mutation harness change one use, never this header
// or another family's accessor. Production calls omit the template argument.
#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class ActorFields {
  public:
    ActorFields(Memory &memory, ActorToken token) : memory_(memory), token_(token) {}
    operator ActorToken() const { return token_; }
    CLAW_RECOVERED_FIELD(holder, offsetof(ActorPrefixLayout, logicHolder))
  private:
    Memory &memory_;
    ActorToken token_;
};

template<class Memory> class LogicHolderFields {
  public:
    LogicHolderFields(Memory &memory, LogicHolderToken token) : memory_(memory), token_(token) {}
    operator LogicHolderToken() const { return token_; }
    CLAW_RECOVERED_FIELD(logic, offsetof(LogicHolderPrefixLayout, logic))
    CLAW_RECOVERED_FIELD(state, offsetof(LogicHolderPrefixLayout, state))
  private:
    Memory &memory_;
    LogicHolderToken token_;
};

template<class Memory> class ActorContextFields {
  public:
    ActorContextFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    operator uint32_t() const { return token_; }
    CLAW_RECOVERED_FIELD(actor, offsetof(ActorContextPrefixLayout, actor))
    CLAW_RECOVERED_FIELD(actorAlias, offsetof(ActorContextPrefixLayout, actorAlias))
    CLAW_RECOVERED_FIELD(holder, offsetof(ActorContextPrefixLayout, logicHolder))
  private:
    Memory &memory_;
    uint32_t token_;
};

// Player/checkpoint/save chain: generator fields observed at 0x49bfb0,
// 0x49c000 and 0x49c030. This prefix is not a complete persisted-record schema.
struct CheckpointByteGeneratorPrefixLayout {
    uint8_t unknown_before_0x44[0x44];
    uint32_t seed;
    uint32_t upperBound;
    uint32_t feedbackBit;
    uint32_t polynomial;
    uint32_t state;
};

static_assert(std::is_standard_layout<CheckpointByteGeneratorPrefixLayout>::value,
              "layout contract");
static_assert(sizeof(CheckpointByteGeneratorPrefixLayout) == 0x58 &&
              alignof(CheckpointByteGeneratorPrefixLayout) == 4,
              "v1.0 checkpoint byte-generator prefix");
static_assert(offsetof(CheckpointByteGeneratorPrefixLayout, seed) == 0x44, "0x49c039");
static_assert(offsetof(CheckpointByteGeneratorPrefixLayout, upperBound) == 0x48, "0x49bfb9 / 0x49c004");
static_assert(offsetof(CheckpointByteGeneratorPrefixLayout, feedbackBit) == 0x4c, "0x49bfbc / 0x49c000");
static_assert(offsetof(CheckpointByteGeneratorPrefixLayout, polynomial) == 0x50, "0x49bfdb / 0x49c014");
static_assert(offsetof(CheckpointByteGeneratorPrefixLayout, state) == 0x54, "0x49bfec / 0x49c008");

template<class Memory> class CheckpointByteGeneratorFields {
  public:
    CheckpointByteGeneratorFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(seed, offsetof(CheckpointByteGeneratorPrefixLayout, seed))
    CLAW_RECOVERED_FIELD(upperBound, offsetof(CheckpointByteGeneratorPrefixLayout, upperBound))
    CLAW_RECOVERED_FIELD(feedbackBit, offsetof(CheckpointByteGeneratorPrefixLayout, feedbackBit))
    CLAW_RECOVERED_FIELD(polynomial, offsetof(CheckpointByteGeneratorPrefixLayout, polynomial))
    CLAW_RECOVERED_FIELD(state, offsetof(CheckpointByteGeneratorPrefixLayout, state))
  private:
    Memory &memory_;
    uint32_t token_;
};

// Observed save layouts are byte-position contracts, never guest overlays.
struct ProfileRecordPrefixLayout {
    uint32_t vtable;
    uint32_t flags;
    uint32_t version;
};
static_assert(std::is_standard_layout<ProfileRecordPrefixLayout>::value, "layout contract");
static_assert(sizeof(ProfileRecordPrefixLayout) == 0xc && alignof(ProfileRecordPrefixLayout) == 4, "v1.0 observed save layout");
static_assert(offsetof(ProfileRecordPrefixLayout, vtable) == 0x0, "save_load original field contract");
static_assert(offsetof(ProfileRecordPrefixLayout, flags) == 0x4, "save_load original field contract");
static_assert(offsetof(ProfileRecordPrefixLayout, version) == 0x8, "save_load original field contract");

template<class Memory> class ProfileRecordFields {
  public:
    ProfileRecordFields(Memory &memory, ProfileRecordToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(vtable, offsetof(ProfileRecordPrefixLayout, vtable))
    CLAW_RECOVERED_FIELD(flags, offsetof(ProfileRecordPrefixLayout, flags))
    CLAW_RECOVERED_FIELD(version, offsetof(ProfileRecordPrefixLayout, version))
  private:
    Memory &memory_;
    ProfileRecordToken token_;
};

struct SaveManagerPrefixLayout {
    uint32_t unknown_0x0;
    uint32_t head;
    uint8_t unknown_before_0x1c[0x14];
    uint32_t pathData;
    uint32_t unknown_0x20;
    uint32_t payloadChecksum;
    uint32_t selection;
    uint32_t recordCount;
    uint8_t unknown_before_0x40[0x10];
    uint32_t unknown_0x40;
};
static_assert(std::is_standard_layout<SaveManagerPrefixLayout>::value, "layout contract");
static_assert(sizeof(SaveManagerPrefixLayout) == 0x44 && alignof(SaveManagerPrefixLayout) == 4, "v1.0 observed save layout");
static_assert(offsetof(SaveManagerPrefixLayout, unknown_0x0) == 0x0, "save_load original field contract");
static_assert(offsetof(SaveManagerPrefixLayout, head) == 0x4, "save_load original field contract");
static_assert(offsetof(SaveManagerPrefixLayout, pathData) == 0x1c, "save_load original field contract");
static_assert(offsetof(SaveManagerPrefixLayout, unknown_0x20) == 0x20, "save_load original field contract");
static_assert(offsetof(SaveManagerPrefixLayout, payloadChecksum) == 0x24, "save_load original field contract");
static_assert(offsetof(SaveManagerPrefixLayout, selection) == 0x28, "save_load original field contract");
static_assert(offsetof(SaveManagerPrefixLayout, recordCount) == 0x2c, "save_load original field contract");
static_assert(offsetof(SaveManagerPrefixLayout, unknown_0x40) == 0x40, "save_load original field contract");

template<class Memory> class SaveManagerFields {
  public:
    SaveManagerFields(Memory &memory, SaveManagerToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(head, offsetof(SaveManagerPrefixLayout, head))
    CLAW_RECOVERED_FIELD(pathData, offsetof(SaveManagerPrefixLayout, pathData))
    CLAW_RECOVERED_FIELD(payloadChecksum, offsetof(SaveManagerPrefixLayout, payloadChecksum))
    CLAW_RECOVERED_FIELD(selection, offsetof(SaveManagerPrefixLayout, selection))
    CLAW_RECOVERED_FIELD(recordCount, offsetof(SaveManagerPrefixLayout, recordCount))
    CLAW_RECOVERED_FIELD(unknown_0x40, offsetof(SaveManagerPrefixLayout, unknown_0x40))
  private:
    Memory &memory_;
    SaveManagerToken token_;
};

struct ProfileListNodeLayout {
    uint32_t next;
    uint32_t unknown_0x4;
    uint32_t record;
};
static_assert(std::is_standard_layout<ProfileListNodeLayout>::value, "layout contract");
static_assert(sizeof(ProfileListNodeLayout) == 0xc && alignof(ProfileListNodeLayout) == 4, "v1.0 observed save layout");
static_assert(offsetof(ProfileListNodeLayout, next) == 0x0, "save_load original field contract");
static_assert(offsetof(ProfileListNodeLayout, unknown_0x4) == 0x4, "save_load original field contract");
static_assert(offsetof(ProfileListNodeLayout, record) == 0x8, "save_load original field contract");

template<class Memory> class ProfileListNodeFields {
  public:
    ProfileListNodeFields(Memory &memory, ProfileListNodeToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(next, offsetof(ProfileListNodeLayout, next))
    CLAW_RECOVERED_FIELD(record, offsetof(ProfileListNodeLayout, record))
  private:
    Memory &memory_;
    ProfileListNodeToken token_;
};

struct ProfileChecksumLayout {
    uint32_t unknown_0x0;
    uint32_t checksum;
    uint8_t unknown_before_0x1c[0x14];
    uint32_t terms[10];
};
static_assert(std::is_standard_layout<ProfileChecksumLayout>::value, "layout contract");
static_assert(sizeof(ProfileChecksumLayout) == 0x44 && alignof(ProfileChecksumLayout) == 4, "v1.0 observed save layout");
static_assert(offsetof(ProfileChecksumLayout, unknown_0x0) == 0x0, "save_load original field contract");
static_assert(offsetof(ProfileChecksumLayout, checksum) == 0x4, "save_load original field contract");
static_assert(offsetof(ProfileChecksumLayout, terms) == 0x1c, "save_load original field contract");

template<class Memory> class ProfileChecksumFields {
  public:
    ProfileChecksumFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(checksum, offsetof(ProfileChecksumLayout, checksum))
  private:
    Memory &memory_;
    uint32_t token_;
};

// Selected-player application handoff (player_cache_application). The list
// count is +0xc here; this separate view makes no claim about SaveManager
// payload recordCount at +0x2c. Cache words retain unknown byte-offset names.
struct ApplicationPlayerPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t windowOwner;
    uint32_t moduleOwner;
    uint8_t unknown_before_0x30[0x24];
    uint32_t scene;
    uint8_t unknown_before_0x60[0x2c];
    uint32_t playerManager;
    uint32_t currentPlayer;
};
static_assert(std::is_standard_layout<ApplicationPlayerPrefixLayout>::value, "layout contract");
static_assert(sizeof(ApplicationPlayerPrefixLayout) == 0x68 && alignof(ApplicationPlayerPrefixLayout) == 4, "v1.0 selected-player byte layout");
static_assert(offsetof(ApplicationPlayerPrefixLayout, windowOwner) == 0x4, "player_cache_application original field");
static_assert(offsetof(ApplicationPlayerPrefixLayout, moduleOwner) == 0x8, "player_cache_application original field");
static_assert(offsetof(ApplicationPlayerPrefixLayout, scene) == 0x30, "player_cache_application original field");
static_assert(offsetof(ApplicationPlayerPrefixLayout, playerManager) == 0x60, "player_cache_application original field");
static_assert(offsetof(ApplicationPlayerPrefixLayout, currentPlayer) == 0x64, "player_cache_application original field");

template<class Memory> class ApplicationPlayerFields {
  public:
    ApplicationPlayerFields(Memory &memory, ApplicationPlayerToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(windowOwner, offsetof(ApplicationPlayerPrefixLayout, windowOwner))
    CLAW_RECOVERED_FIELD(moduleOwner, offsetof(ApplicationPlayerPrefixLayout, moduleOwner))
    CLAW_RECOVERED_FIELD(scene, offsetof(ApplicationPlayerPrefixLayout, scene))
    CLAW_RECOVERED_FIELD(playerManager, offsetof(ApplicationPlayerPrefixLayout, playerManager))
    CLAW_RECOVERED_FIELD(currentPlayer, offsetof(ApplicationPlayerPrefixLayout, currentPlayer))
  private:
    Memory &memory_;
    ApplicationPlayerToken token_;
};

struct PlayerListManagerPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t head;
    uint8_t unknown_before_0xc[0x4];
    uint32_t count;
};
static_assert(std::is_standard_layout<PlayerListManagerPrefixLayout>::value, "layout contract");
static_assert(sizeof(PlayerListManagerPrefixLayout) == 0x10 && alignof(PlayerListManagerPrefixLayout) == 4, "v1.0 selected-player byte layout");
static_assert(offsetof(PlayerListManagerPrefixLayout, head) == 0x4, "player_cache_application original field");
static_assert(offsetof(PlayerListManagerPrefixLayout, count) == 0xc, "player_cache_application original field");

template<class Memory> class PlayerListManagerFields {
  public:
    PlayerListManagerFields(Memory &memory, PlayerListManagerToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(head, offsetof(PlayerListManagerPrefixLayout, head))
    CLAW_RECOVERED_FIELD(count, offsetof(PlayerListManagerPrefixLayout, count))
  private:
    Memory &memory_;
    PlayerListManagerToken token_;
};

struct PlayerCachePrefixLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t unknown_0x10;
    uint32_t unknown_0x14;
    uint32_t unknown_0x18;
    uint32_t unknown_0x1c;
    uint32_t unknown_0x20;
    uint32_t unknown_0x24;
    uint32_t unknown_0x28;
    uint32_t unknown_0x2c;
    uint32_t unknown_0x30;
    uint32_t unknown_0x34;
    uint8_t unknown_before_0x48[0x10];
    uint32_t unknown_0x48;
    uint32_t unknown_0x4c;
    uint32_t unknown_0x50;
    uint32_t unknown_0x54;
    uint32_t unknown_0x58;
    uint32_t unknown_0x5c;
    uint32_t unknown_0x60;
    uint32_t unknown_0x64;
    uint32_t unknown_0x68;
    uint32_t unknown_0x6c;
};
static_assert(std::is_standard_layout<PlayerCachePrefixLayout>::value, "layout contract");
static_assert(sizeof(PlayerCachePrefixLayout) == 0x70 && alignof(PlayerCachePrefixLayout) == 4, "v1.0 selected-player byte layout");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x10) == 0x10, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x14) == 0x14, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x18) == 0x18, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x1c) == 0x1c, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x20) == 0x20, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x24) == 0x24, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x28) == 0x28, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x2c) == 0x2c, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x30) == 0x30, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x34) == 0x34, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x48) == 0x48, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x4c) == 0x4c, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x50) == 0x50, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x54) == 0x54, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x58) == 0x58, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x5c) == 0x5c, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x60) == 0x60, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x64) == 0x64, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x68) == 0x68, "player_cache_application original field");
static_assert(offsetof(PlayerCachePrefixLayout, unknown_0x6c) == 0x6c, "player_cache_application original field");

template<class Memory> class PlayerCacheFields {
  public:
    PlayerCacheFields(Memory &memory, PlayerCacheToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x10, offsetof(PlayerCachePrefixLayout, unknown_0x10))
    CLAW_RECOVERED_FIELD(unknown_0x14, offsetof(PlayerCachePrefixLayout, unknown_0x14))
    CLAW_RECOVERED_FIELD(unknown_0x18, offsetof(PlayerCachePrefixLayout, unknown_0x18))
    CLAW_RECOVERED_FIELD(unknown_0x1c, offsetof(PlayerCachePrefixLayout, unknown_0x1c))
    CLAW_RECOVERED_FIELD(unknown_0x20, offsetof(PlayerCachePrefixLayout, unknown_0x20))
    CLAW_RECOVERED_FIELD(unknown_0x24, offsetof(PlayerCachePrefixLayout, unknown_0x24))
    CLAW_RECOVERED_FIELD(unknown_0x28, offsetof(PlayerCachePrefixLayout, unknown_0x28))
    CLAW_RECOVERED_FIELD(unknown_0x2c, offsetof(PlayerCachePrefixLayout, unknown_0x2c))
    CLAW_RECOVERED_FIELD(unknown_0x30, offsetof(PlayerCachePrefixLayout, unknown_0x30))
    CLAW_RECOVERED_FIELD(unknown_0x34, offsetof(PlayerCachePrefixLayout, unknown_0x34))
    CLAW_RECOVERED_FIELD(unknown_0x48, offsetof(PlayerCachePrefixLayout, unknown_0x48))
    CLAW_RECOVERED_FIELD(unknown_0x4c, offsetof(PlayerCachePrefixLayout, unknown_0x4c))
    CLAW_RECOVERED_FIELD(unknown_0x50, offsetof(PlayerCachePrefixLayout, unknown_0x50))
    CLAW_RECOVERED_FIELD(unknown_0x54, offsetof(PlayerCachePrefixLayout, unknown_0x54))
    CLAW_RECOVERED_FIELD(unknown_0x58, offsetof(PlayerCachePrefixLayout, unknown_0x58))
    CLAW_RECOVERED_FIELD(unknown_0x5c, offsetof(PlayerCachePrefixLayout, unknown_0x5c))
    CLAW_RECOVERED_FIELD(unknown_0x60, offsetof(PlayerCachePrefixLayout, unknown_0x60))
    CLAW_RECOVERED_FIELD(unknown_0x64, offsetof(PlayerCachePrefixLayout, unknown_0x64))
    CLAW_RECOVERED_FIELD(unknown_0x68, offsetof(PlayerCachePrefixLayout, unknown_0x68))
    CLAW_RECOVERED_FIELD(unknown_0x6c, offsetof(PlayerCachePrefixLayout, unknown_0x6c))
  private:
    Memory &memory_;
    PlayerCacheToken token_;
};

struct ProfileCacheRecordPrefixLayout {
    uint8_t unknown_before_0x25d4[0x25d4];
    uint32_t unknown_0x25d4;
    uint32_t unknown_0x25d8;
    uint32_t unknown_0x25dc;
    uint32_t unknown_0x25e0;
    uint32_t unknown_0x25e4;
    uint32_t unknown_0x25e8;
    uint32_t unknown_0x25ec;
    uint32_t unknown_0x25f0;
    uint32_t unknown_0x25f4;
    uint32_t unknown_0x25f8;
    uint8_t unknown_before_0x2618[0x1c];
    uint32_t unknown_0x2618;
    uint32_t unknown_0x261c;
    uint32_t unknown_0x2620;
    uint32_t unknown_0x2624;
    uint32_t unknown_0x2628;
    uint32_t unknown_0x262c;
    uint32_t unknown_0x2630;
    uint32_t unknown_0x2634;
    uint32_t unknown_0x2638;
    uint32_t unknown_0x263c;
};
static_assert(std::is_standard_layout<ProfileCacheRecordPrefixLayout>::value, "layout contract");
static_assert(sizeof(ProfileCacheRecordPrefixLayout) == 0x2640 && alignof(ProfileCacheRecordPrefixLayout) == 4, "v1.0 selected-player byte layout");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25d4) == 0x25d4, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25d8) == 0x25d8, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25dc) == 0x25dc, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25e0) == 0x25e0, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25e4) == 0x25e4, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25e8) == 0x25e8, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25ec) == 0x25ec, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25f0) == 0x25f0, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25f4) == 0x25f4, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25f8) == 0x25f8, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2618) == 0x2618, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x261c) == 0x261c, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2620) == 0x2620, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2624) == 0x2624, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2628) == 0x2628, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x262c) == 0x262c, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2630) == 0x2630, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2634) == 0x2634, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2638) == 0x2638, "player_cache_application original field");
static_assert(offsetof(ProfileCacheRecordPrefixLayout, unknown_0x263c) == 0x263c, "player_cache_application original field");

template<class Memory> class ProfileCacheRecordFields {
  public:
    ProfileCacheRecordFields(Memory &memory, ProfileRecordToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x25d4, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25d4))
    CLAW_RECOVERED_FIELD(unknown_0x25d8, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25d8))
    CLAW_RECOVERED_FIELD(unknown_0x25dc, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25dc))
    CLAW_RECOVERED_FIELD(unknown_0x25e0, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25e0))
    CLAW_RECOVERED_FIELD(unknown_0x25e4, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25e4))
    CLAW_RECOVERED_FIELD(unknown_0x25e8, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25e8))
    CLAW_RECOVERED_FIELD(unknown_0x25ec, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25ec))
    CLAW_RECOVERED_FIELD(unknown_0x25f0, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25f0))
    CLAW_RECOVERED_FIELD(unknown_0x25f4, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25f4))
    CLAW_RECOVERED_FIELD(unknown_0x25f8, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x25f8))
    CLAW_RECOVERED_FIELD(unknown_0x2618, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2618))
    CLAW_RECOVERED_FIELD(unknown_0x261c, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x261c))
    CLAW_RECOVERED_FIELD(unknown_0x2620, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2620))
    CLAW_RECOVERED_FIELD(unknown_0x2624, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2624))
    CLAW_RECOVERED_FIELD(unknown_0x2628, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2628))
    CLAW_RECOVERED_FIELD(unknown_0x262c, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x262c))
    CLAW_RECOVERED_FIELD(unknown_0x2630, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2630))
    CLAW_RECOVERED_FIELD(unknown_0x2634, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2634))
    CLAW_RECOVERED_FIELD(unknown_0x2638, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x2638))
    CLAW_RECOVERED_FIELD(unknown_0x263c, offsetof(ProfileCacheRecordPrefixLayout, unknown_0x263c))
  private:
    Memory &memory_;
    ProfileRecordToken token_;
};


// Player/checkpoint/save/death chain: original v1.0 respawn cleanup 0x46e340.
// An observed byte-layout contract, never an overlay on guest storage. Only
// the two flag words touched by this callback are named here.
struct RespawnCleanupActorPrefixLayout {
    uint8_t unknown_before_0x8[0x8];
    uint32_t removalFlags;
    uint8_t unknown_before_0x164[0x158];
    uint32_t cleanupFlags;
};
static_assert(std::is_standard_layout<RespawnCleanupActorPrefixLayout>::value,
              "v1.0 cleanup layout contract");
static_assert(sizeof(RespawnCleanupActorPrefixLayout) == 0x168 &&
              alignof(RespawnCleanupActorPrefixLayout) == 4,
              "v1.0 observed cleanup actor prefix");
static_assert(offsetof(RespawnCleanupActorPrefixLayout, removalFlags) == 0x8,
              "0x46e353 removal flag word");
static_assert(offsetof(RespawnCleanupActorPrefixLayout, cleanupFlags) == 0x164,
              "0x46e348 cleanup eligibility flag word");

template<class Memory> class RespawnCleanupActorFields {
  public:
    RespawnCleanupActorFields(Memory &memory, ActorToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(removalFlags, offsetof(RespawnCleanupActorPrefixLayout, removalFlags))
    CLAW_RECOVERED_FIELD(cleanupFlags, offsetof(RespawnCleanupActorPrefixLayout, cleanupFlags))
  private:
    Memory &memory_;
    ActorToken token_;
};


// Death messages and their existing player/network services. These contracts
// describe only observed prefixes; no native overlay or allocation is created.
struct DeathApplicationPrefixLayout {
    uint8_t unknown_before_0x2c[0x2c];
    uint32_t messageManager;
};
static_assert(std::is_standard_layout<DeathApplicationPrefixLayout>::value, "layout contract");
static_assert(sizeof(DeathApplicationPrefixLayout) == 0x30 && alignof(DeathApplicationPrefixLayout) == 4, "v1.0 death-service prefix");
static_assert(offsetof(DeathApplicationPrefixLayout, messageManager) == 0x2c, "level_one_batch_claw_death_01 original field");

template<class Memory> class DeathApplicationFields {
  public:
    DeathApplicationFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(messageManager, offsetof(DeathApplicationPrefixLayout, messageManager))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PlayerMessageManagerPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t parent;
    uint8_t unknown_before_0x780[0x778];
    uint32_t playerList;
    uint32_t currentPlayer;
    uint32_t currentPlayerKey;
    uint8_t unknown_before_0xbc8[0x43c];
    uint32_t sendRecord;
};
static_assert(std::is_standard_layout<PlayerMessageManagerPrefixLayout>::value, "layout contract");
static_assert(sizeof(PlayerMessageManagerPrefixLayout) == 0xbcc && alignof(PlayerMessageManagerPrefixLayout) == 4, "v1.0 death-service prefix");
static_assert(offsetof(PlayerMessageManagerPrefixLayout, parent) == 0x4, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(PlayerMessageManagerPrefixLayout, playerList) == 0x780, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(PlayerMessageManagerPrefixLayout, currentPlayer) == 0x784, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(PlayerMessageManagerPrefixLayout, currentPlayerKey) == 0x788, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(PlayerMessageManagerPrefixLayout, sendRecord) == 0xbc8, "level_one_batch_claw_death_01 original field");

template<class Memory> class PlayerMessageManagerFields {
  public:
    PlayerMessageManagerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(parent, offsetof(PlayerMessageManagerPrefixLayout, parent))
    CLAW_RECOVERED_FIELD(playerList, offsetof(PlayerMessageManagerPrefixLayout, playerList))
    CLAW_RECOVERED_FIELD(currentPlayer, offsetof(PlayerMessageManagerPrefixLayout, currentPlayer))
    CLAW_RECOVERED_FIELD(currentPlayerKey, offsetof(PlayerMessageManagerPrefixLayout, currentPlayerKey))
    CLAW_RECOVERED_FIELD(sendRecord, offsetof(PlayerMessageManagerPrefixLayout, sendRecord))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct MessagePlayerPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t key;
    uint32_t nameData;
    uint8_t unknown_before_0x18[0xc];
    uint32_t buffer;
    uint32_t bufferBytes;
};
static_assert(std::is_standard_layout<MessagePlayerPrefixLayout>::value, "layout contract");
static_assert(sizeof(MessagePlayerPrefixLayout) == 0x20 && alignof(MessagePlayerPrefixLayout) == 4, "v1.0 death-service prefix");
static_assert(offsetof(MessagePlayerPrefixLayout, key) == 0x4, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(MessagePlayerPrefixLayout, nameData) == 0x8, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(MessagePlayerPrefixLayout, buffer) == 0x18, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(MessagePlayerPrefixLayout, bufferBytes) == 0x1c, "level_one_batch_claw_death_01 original field");

template<class Memory> class MessagePlayerFields {
  public:
    MessagePlayerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(key, offsetof(MessagePlayerPrefixLayout, key))
    CLAW_RECOVERED_FIELD(buffer, offsetof(MessagePlayerPrefixLayout, buffer))
    CLAW_RECOVERED_FIELD(bufferBytes, offsetof(MessagePlayerPrefixLayout, bufferBytes))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct MessagePlayerListPrefixLayout {
    uint8_t unknown_before_0x18[0x18];
    uint32_t transport;
    uint8_t unknown_before_0x58[0x3c];
    uint32_t head;
};
static_assert(std::is_standard_layout<MessagePlayerListPrefixLayout>::value, "layout contract");
static_assert(sizeof(MessagePlayerListPrefixLayout) == 0x5c && alignof(MessagePlayerListPrefixLayout) == 4, "v1.0 death-service prefix");
static_assert(offsetof(MessagePlayerListPrefixLayout, transport) == 0x18, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(MessagePlayerListPrefixLayout, head) == 0x58, "level_one_batch_claw_death_01 original field");

template<class Memory> class MessagePlayerListFields {
  public:
    MessagePlayerListFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(transport, offsetof(MessagePlayerListPrefixLayout, transport))
    CLAW_RECOVERED_FIELD(head, offsetof(MessagePlayerListPrefixLayout, head))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct MessagePlayerNodeLayout {
    uint32_t next;
    uint8_t unknown_before_0x8[0x4];
    uint32_t player;
};
static_assert(std::is_standard_layout<MessagePlayerNodeLayout>::value, "layout contract");
static_assert(sizeof(MessagePlayerNodeLayout) == 0xc && alignof(MessagePlayerNodeLayout) == 4, "v1.0 death-service prefix");
static_assert(offsetof(MessagePlayerNodeLayout, next) == 0x0, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(MessagePlayerNodeLayout, player) == 0x8, "level_one_batch_claw_death_01 original field");

template<class Memory> class MessagePlayerNodeFields {
  public:
    MessagePlayerNodeFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(next, offsetof(MessagePlayerNodeLayout, next))
    CLAW_RECOVERED_FIELD(player, offsetof(MessagePlayerNodeLayout, player))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct MessageParentPrefixLayout {
    uint8_t unknown_before_0x4c[0x4c];
    uint32_t window;
};
static_assert(std::is_standard_layout<MessageParentPrefixLayout>::value, "layout contract");
static_assert(sizeof(MessageParentPrefixLayout) == 0x50 && alignof(MessageParentPrefixLayout) == 4, "v1.0 death-service prefix");
static_assert(offsetof(MessageParentPrefixLayout, window) == 0x4c, "level_one_batch_claw_death_01 original field");

template<class Memory> class MessageParentFields {
  public:
    MessageParentFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(window, offsetof(MessageParentPrefixLayout, window))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PlayerMessageRecordPrefixLayout {
    uint32_t kind;
    uint32_t id;
};
static_assert(std::is_standard_layout<PlayerMessageRecordPrefixLayout>::value, "layout contract");
static_assert(sizeof(PlayerMessageRecordPrefixLayout) == 0x8 && alignof(PlayerMessageRecordPrefixLayout) == 4, "v1.0 death-service prefix");
static_assert(offsetof(PlayerMessageRecordPrefixLayout, kind) == 0x0, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(PlayerMessageRecordPrefixLayout, id) == 0x4, "level_one_batch_claw_death_01 original field");

template<class Memory> class PlayerMessageRecordFields {
  public:
    PlayerMessageRecordFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(kind, offsetof(PlayerMessageRecordPrefixLayout, kind))
    CLAW_RECOVERED_FIELD(id, offsetof(PlayerMessageRecordPrefixLayout, id))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct NetworkErrorPrefixLayout {
    uint32_t formatDetails;
    uint32_t showDialog;
    uint32_t beep;
    uint32_t unknown_0xc;
    uint32_t code;
    uint32_t lowCode;
};
static_assert(std::is_standard_layout<NetworkErrorPrefixLayout>::value, "layout contract");
static_assert(sizeof(NetworkErrorPrefixLayout) == 0x18 && alignof(NetworkErrorPrefixLayout) == 4, "v1.0 death-service prefix");
static_assert(offsetof(NetworkErrorPrefixLayout, formatDetails) == 0x0, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(NetworkErrorPrefixLayout, showDialog) == 0x4, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(NetworkErrorPrefixLayout, beep) == 0x8, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(NetworkErrorPrefixLayout, unknown_0xc) == 0xc, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(NetworkErrorPrefixLayout, code) == 0x10, "level_one_batch_claw_death_01 original field");
static_assert(offsetof(NetworkErrorPrefixLayout, lowCode) == 0x14, "level_one_batch_claw_death_01 original field");

template<class Memory> class NetworkErrorFields {
  public:
    NetworkErrorFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(formatDetails, offsetof(NetworkErrorPrefixLayout, formatDetails))
    CLAW_RECOVERED_FIELD(showDialog, offsetof(NetworkErrorPrefixLayout, showDialog))
    CLAW_RECOVERED_FIELD(beep, offsetof(NetworkErrorPrefixLayout, beep))
    CLAW_RECOVERED_FIELD(unknown_0xc, offsetof(NetworkErrorPrefixLayout, unknown_0xc))
    CLAW_RECOVERED_FIELD(code, offsetof(NetworkErrorPrefixLayout, code))
    CLAW_RECOVERED_FIELD(lowCode, offsetof(NetworkErrorPrefixLayout, lowCode))
  private:
    Memory &memory_;
    uint32_t token_;
};


// Player powerup lifecycle: observed v1.0 byte-position contracts. The
// +0x170 owner of a GlitterMother record is distinct from a player's range.
// These prefixes are never overlaid on guest memory or used for allocation.
struct PowerupGlobalsLayout {
    uint32_t amount;
    uint32_t kind;
    uint8_t unknown_before_0x20[0x18];
    uint32_t flareCountdown;
    uint32_t flareFrame;
};
static_assert(std::is_standard_layout<PowerupGlobalsLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(PowerupGlobalsLayout) == 0x28 && alignof(PowerupGlobalsLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(PowerupGlobalsLayout, amount) == 0x0, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupGlobalsLayout, kind) == 0x4, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupGlobalsLayout, flareCountdown) == 0x20, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupGlobalsLayout, flareFrame) == 0x24, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class PowerupGlobalsFields {
  public:
    PowerupGlobalsFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(amount, offsetof(PowerupGlobalsLayout, amount))
    CLAW_RECOVERED_FIELD(kind, offsetof(PowerupGlobalsLayout, kind))
    CLAW_RECOVERED_FIELD(flareCountdown, offsetof(PowerupGlobalsLayout, flareCountdown))
    CLAW_RECOVERED_FIELD(flareFrame, offsetof(PowerupGlobalsLayout, flareFrame))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PowerupApplicationLayout {
    uint8_t unknown_before_0x14[0x14];
    uint32_t unknown_0x14;
    uint8_t unknown_before_0x50[0x38];
    uint32_t musicEntries;
};
static_assert(std::is_standard_layout<PowerupApplicationLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(PowerupApplicationLayout) == 0x54 && alignof(PowerupApplicationLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(PowerupApplicationLayout, unknown_0x14) == 0x14, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupApplicationLayout, musicEntries) == 0x50, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class PowerupApplicationFields {
  public:
    PowerupApplicationFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x14, offsetof(PowerupApplicationLayout, unknown_0x14))
    CLAW_RECOVERED_FIELD(musicEntries, offsetof(PowerupApplicationLayout, musicEntries))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PowerupMusicManagerLayout {
    uint8_t unknown_before_0x1c[0x1c];
    uint32_t currentEntry;
};
static_assert(std::is_standard_layout<PowerupMusicManagerLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(PowerupMusicManagerLayout) == 0x20 && alignof(PowerupMusicManagerLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(PowerupMusicManagerLayout, currentEntry) == 0x1c, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class PowerupMusicManagerFields {
  public:
    PowerupMusicManagerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(currentEntry, offsetof(PowerupMusicManagerLayout, currentEntry))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PowerupPlayerLayout {
    uint8_t unknown_before_0xc[0xc];
    uint32_t unknown_0xc;
    uint8_t unknown_before_0xd4[0xc4];
    uint32_t unknown_0xd4;
    uint8_t unknown_before_0x170[0x98];
    uint32_t attachmentRange;
    uint32_t flareAttachment;
};
static_assert(std::is_standard_layout<PowerupPlayerLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(PowerupPlayerLayout) == 0x178 && alignof(PowerupPlayerLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(PowerupPlayerLayout, unknown_0xc) == 0xc, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupPlayerLayout, unknown_0xd4) == 0xd4, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupPlayerLayout, attachmentRange) == 0x170, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupPlayerLayout, flareAttachment) == 0x174, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class PowerupPlayerFields {
  public:
    PowerupPlayerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0xc, offsetof(PowerupPlayerLayout, unknown_0xc))
    CLAW_RECOVERED_FIELD(unknown_0xd4, offsetof(PowerupPlayerLayout, unknown_0xd4))
    CLAW_RECOVERED_FIELD(attachmentRange, offsetof(PowerupPlayerLayout, attachmentRange))
    CLAW_RECOVERED_FIELD(flareAttachment, offsetof(PowerupPlayerLayout, flareAttachment))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PowerupStateLayout {
    uint8_t unknown_before_0x130[0x130];
    uint32_t glitterMother;
};
static_assert(std::is_standard_layout<PowerupStateLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(PowerupStateLayout) == 0x134 && alignof(PowerupStateLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(PowerupStateLayout, glitterMother) == 0x130, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class PowerupStateFields {
  public:
    PowerupStateFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(glitterMother, offsetof(PowerupStateLayout, glitterMother))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct GlitterMotherOwnerContextLayout {
    uint8_t unknown_before_0x8[0x8];
    uint32_t creationManager;
};
static_assert(std::is_standard_layout<GlitterMotherOwnerContextLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(GlitterMotherOwnerContextLayout) == 0xc && alignof(GlitterMotherOwnerContextLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(GlitterMotherOwnerContextLayout, creationManager) == 0x8, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class GlitterMotherOwnerContextFields {
  public:
    GlitterMotherOwnerContextFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(creationManager, offsetof(GlitterMotherOwnerContextLayout, creationManager))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct GlitterMotherRecordLayout {
    uint8_t unknown_before_0x170[0x170];
    uint32_t owner;
};
static_assert(std::is_standard_layout<GlitterMotherRecordLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(GlitterMotherRecordLayout) == 0x174 && alignof(GlitterMotherRecordLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(GlitterMotherRecordLayout, owner) == 0x170, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class GlitterMotherRecordFields {
  public:
    GlitterMotherRecordFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(owner, offsetof(GlitterMotherRecordLayout, owner))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PowerupRemovalLayout {
    uint8_t unknown_before_0x8[0x8];
    uint32_t unknown_0x8;
};
static_assert(std::is_standard_layout<PowerupRemovalLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(PowerupRemovalLayout) == 0xc && alignof(PowerupRemovalLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(PowerupRemovalLayout, unknown_0x8) == 0x8, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class PowerupRemovalFields {
  public:
    PowerupRemovalFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x8, offsetof(PowerupRemovalLayout, unknown_0x8))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PowerupAttachmentLayout {
    uint8_t unknown_before_0x30[0x30];
    uint32_t messageTarget;
};
static_assert(std::is_standard_layout<PowerupAttachmentLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(PowerupAttachmentLayout) == 0x34 && alignof(PowerupAttachmentLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(PowerupAttachmentLayout, messageTarget) == 0x30, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class PowerupAttachmentFields {
  public:
    PowerupAttachmentFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(messageTarget, offsetof(PowerupAttachmentLayout, messageTarget))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct FlareSpriteLayout {
    uint8_t unknown_before_0x18[0x18];
    uint32_t frame;
};
static_assert(std::is_standard_layout<FlareSpriteLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(FlareSpriteLayout) == 0x1c && alignof(FlareSpriteLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(FlareSpriteLayout, frame) == 0x18, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class FlareSpriteFields {
  public:
    FlareSpriteFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(frame, offsetof(FlareSpriteLayout, frame))
  private:
    Memory &memory_;
    uint32_t token_;
};

struct PowerupAttachmentRangeLayout {
    uint8_t unknown_before_0x14[0x14];
    uint32_t slots;
    uint8_t unknown_before_0x64[0x4c];
    uint32_t firstIndex;
    uint32_t lastIndex;
};
static_assert(std::is_standard_layout<PowerupAttachmentRangeLayout>::value, "v1.0 observed powerup prefix");
static_assert(sizeof(PowerupAttachmentRangeLayout) == 0x6c && alignof(PowerupAttachmentRangeLayout) == 4, "v1.0 observed powerup prefix");
static_assert(offsetof(PowerupAttachmentRangeLayout, slots) == 0x14, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupAttachmentRangeLayout, firstIndex) == 0x64, "level_one_batch_claw_powerups_01 original field");
static_assert(offsetof(PowerupAttachmentRangeLayout, lastIndex) == 0x68, "level_one_batch_claw_powerups_01 original field");

template<class Memory> class PowerupAttachmentRangeFields {
  public:
    PowerupAttachmentRangeFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(slots, offsetof(PowerupAttachmentRangeLayout, slots))
    CLAW_RECOVERED_FIELD(firstIndex, offsetof(PowerupAttachmentRangeLayout, firstIndex))
    CLAW_RECOVERED_FIELD(lastIndex, offsetof(PowerupAttachmentRangeLayout, lastIndex))
  private:
    Memory &memory_;
    uint32_t token_;
};


// End player/checkpoint/save chain.

#undef CLAW_RECOVERED_FIELD


// Actor storage/collision chain: observed v1.0 prefixes, never guest overlays.
struct ActorStoragePrefixLayout {
    uint32_t vtable;
    uint32_t id;
    uint32_t flags;
    uint32_t scene;
    uint8_t unknown_before_0x4c[0x3c];
    uint32_t unknown_0x4c;
    uint8_t unknown_before_0x64[0x14];
    uint32_t depth;
    uint32_t listNode;
    uint32_t primaryHolder;
    uint32_t secondaryHolder;
    uint8_t unknown_before_0x78[0x4];
    uint32_t contactHolder;
    uint8_t unknown_before_0x80[0x4];
    uint32_t unknown_0x80;
    uint32_t unknown_0x84;
};
static_assert(std::is_standard_layout<ActorStoragePrefixLayout>::value, "layout contract");
static_assert(sizeof(ActorStoragePrefixLayout) == 0x88 && alignof(ActorStoragePrefixLayout) == 4, "v1.0 observed storage prefix");
static_assert(offsetof(ActorStoragePrefixLayout, vtable) == 0x0, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, id) == 0x4, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, flags) == 0x8, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, scene) == 0xc, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, unknown_0x4c) == 0x4c, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, depth) == 0x64, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, listNode) == 0x68, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, primaryHolder) == 0x6c, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, secondaryHolder) == 0x70, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, contactHolder) == 0x78, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, unknown_0x80) == 0x80, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorStoragePrefixLayout, unknown_0x84) == 0x84, "level_one_actor_storage_01 original field");

struct ResourceStoragePrefixLayout {
    uint32_t vtable;
    uint32_t id;
    uint32_t flags;
    uint32_t scene;
    uint32_t initializer;
    uint32_t unknown_0x14;
};
static_assert(std::is_standard_layout<ResourceStoragePrefixLayout>::value, "layout contract");
static_assert(sizeof(ResourceStoragePrefixLayout) == 0x18 && alignof(ResourceStoragePrefixLayout) == 4, "v1.0 observed storage prefix");
static_assert(offsetof(ResourceStoragePrefixLayout, vtable) == 0x0, "level_one_actor_storage_01 original field");
static_assert(offsetof(ResourceStoragePrefixLayout, id) == 0x4, "level_one_actor_storage_01 original field");
static_assert(offsetof(ResourceStoragePrefixLayout, flags) == 0x8, "level_one_actor_storage_01 original field");
static_assert(offsetof(ResourceStoragePrefixLayout, scene) == 0xc, "level_one_actor_storage_01 original field");
static_assert(offsetof(ResourceStoragePrefixLayout, initializer) == 0x10, "level_one_actor_storage_01 original field");
static_assert(offsetof(ResourceStoragePrefixLayout, unknown_0x14) == 0x14, "level_one_actor_storage_01 original field");

struct LogicMetadataPrefixLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t initializer;
};
static_assert(std::is_standard_layout<LogicMetadataPrefixLayout>::value, "layout contract");
static_assert(sizeof(LogicMetadataPrefixLayout) == 0x14 && alignof(LogicMetadataPrefixLayout) == 4, "v1.0 observed storage prefix");
static_assert(offsetof(LogicMetadataPrefixLayout, initializer) == 0x10, "level_one_actor_storage_01 original field");

struct ActorStorageScenePrefixLayout {
    uint8_t unknown_before_0x14[0x14];
    uint32_t registry;
};
static_assert(std::is_standard_layout<ActorStorageScenePrefixLayout>::value, "layout contract");
static_assert(sizeof(ActorStorageScenePrefixLayout) == 0x18 && alignof(ActorStorageScenePrefixLayout) == 4, "v1.0 observed storage prefix");
static_assert(offsetof(ActorStorageScenePrefixLayout, registry) == 0x14, "level_one_actor_storage_01 original field");

struct ActorContainerPrefixLayout {
    uint8_t unknown_before_0xc[0xc];
    uint32_t scene;
    uint8_t unknown_before_0x14[0x4];
    uint32_t head;
};
static_assert(std::is_standard_layout<ActorContainerPrefixLayout>::value, "layout contract");
static_assert(sizeof(ActorContainerPrefixLayout) == 0x18 && alignof(ActorContainerPrefixLayout) == 4, "v1.0 observed storage prefix");
static_assert(offsetof(ActorContainerPrefixLayout, scene) == 0xc, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorContainerPrefixLayout, head) == 0x14, "level_one_actor_storage_01 original field");

struct ActorListNodePrefixLayout {
    uint32_t next;
    uint8_t unknown_before_0x8[0x4];
    uint32_t actor;
};
static_assert(std::is_standard_layout<ActorListNodePrefixLayout>::value, "layout contract");
static_assert(sizeof(ActorListNodePrefixLayout) == 0xc && alignof(ActorListNodePrefixLayout) == 4, "v1.0 observed storage prefix");
static_assert(offsetof(ActorListNodePrefixLayout, next) == 0x0, "level_one_actor_storage_01 original field");
static_assert(offsetof(ActorListNodePrefixLayout, actor) == 0x8, "level_one_actor_storage_01 original field");

static_assert(offsetof(ActorStoragePrefixLayout, primaryHolder) == offsetof(ActorPrefixLayout, logicHolder), "shared actor holder contract");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class ActorStorageFields {
  public:
    ActorStorageFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(vtable, offsetof(ActorStoragePrefixLayout, vtable))
    CLAW_RECOVERED_FIELD(id, offsetof(ActorStoragePrefixLayout, id))
    CLAW_RECOVERED_FIELD(flags, offsetof(ActorStoragePrefixLayout, flags))
    CLAW_RECOVERED_FIELD(scene, offsetof(ActorStoragePrefixLayout, scene))
    CLAW_RECOVERED_FIELD(unknown_0x4c, offsetof(ActorStoragePrefixLayout, unknown_0x4c))
    CLAW_RECOVERED_FIELD(depth, offsetof(ActorStoragePrefixLayout, depth))
    CLAW_RECOVERED_FIELD(listNode, offsetof(ActorStoragePrefixLayout, listNode))
    CLAW_RECOVERED_FIELD(secondaryHolder, offsetof(ActorStoragePrefixLayout, secondaryHolder))
    CLAW_RECOVERED_FIELD(contactHolder, offsetof(ActorStoragePrefixLayout, contactHolder))
    CLAW_RECOVERED_FIELD(unknown_0x80, offsetof(ActorStoragePrefixLayout, unknown_0x80))
    CLAW_RECOVERED_FIELD(unknown_0x84, offsetof(ActorStoragePrefixLayout, unknown_0x84))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ResourceStorageFields {
  public:
    ResourceStorageFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(vtable, offsetof(ResourceStoragePrefixLayout, vtable))
    CLAW_RECOVERED_FIELD(id, offsetof(ResourceStoragePrefixLayout, id))
    CLAW_RECOVERED_FIELD(flags, offsetof(ResourceStoragePrefixLayout, flags))
    CLAW_RECOVERED_FIELD(scene, offsetof(ResourceStoragePrefixLayout, scene))
    CLAW_RECOVERED_FIELD(initializer, offsetof(ResourceStoragePrefixLayout, initializer))
    CLAW_RECOVERED_FIELD(unknown_0x14, offsetof(ResourceStoragePrefixLayout, unknown_0x14))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class LogicMetadataFields {
  public:
    LogicMetadataFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(initializer, offsetof(LogicMetadataPrefixLayout, initializer))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ActorStorageSceneFields {
  public:
    ActorStorageSceneFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(registry, offsetof(ActorStorageScenePrefixLayout, registry))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ActorContainerFields {
  public:
    ActorContainerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(scene, offsetof(ActorContainerPrefixLayout, scene))
    CLAW_RECOVERED_FIELD(head, offsetof(ActorContainerPrefixLayout, head))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ActorListNodeFields {
  public:
    ActorListNodeFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(next, offsetof(ActorListNodePrefixLayout, next))
    CLAW_RECOVERED_FIELD(actor, offsetof(ActorListNodePrefixLayout, actor))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

// Observed interaction/projection prefixes from actor-storage batch 2.
struct InteractionCallbackPrefixLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t function;
};
static_assert(std::is_standard_layout<InteractionCallbackPrefixLayout>::value, "layout contract");
static_assert(sizeof(InteractionCallbackPrefixLayout) == 0x14 && alignof(InteractionCallbackPrefixLayout) == 4, "v1.0 observed callback prefix");
static_assert(offsetof(InteractionCallbackPrefixLayout, function) == 0x10, "0x4c94e5 / 0x4c9526 / 0x4c957a / 0x4c9b1e");


struct ActorInteractionPrefixLayout {
    uint8_t unknown_before_0x8[0x8];
    uint32_t flags;
    uint8_t unknown_before_0x4c[0x40];
    uint32_t worldX;
    uint32_t worldY;
    uint8_t unknown_before_0x74[0x20];
    uint32_t hitPeer;
    uint8_t unknown_before_0x7c[0x4];
    uint32_t contactPeer;
    uint8_t unknown_before_0xd0[0x50];
    uint32_t unknown_0xd0;
    uint32_t unknown_0xd4;
    uint32_t unknown_0xd8;
    uint8_t unknown_before_0x104[0x28];
    uint32_t damage;
    uint8_t unknown_before_0x10c[0x4];
    uint32_t health;
    uint8_t unknown_before_0x128[0x18];
    uint32_t hitLeft;
    uint32_t hitTop;
    uint32_t hitRight;
    uint32_t hitBottom;
    uint32_t attackLeft;
    uint32_t attackTop;
    uint32_t attackRight;
    uint32_t attackBottom;
};
static_assert(std::is_standard_layout<ActorInteractionPrefixLayout>::value, "layout contract");
static_assert(sizeof(ActorInteractionPrefixLayout) == 0x148 && alignof(ActorInteractionPrefixLayout) == 4, "v1.0 observed interaction prefix");
static_assert(offsetof(ActorInteractionPrefixLayout, flags) == 0x8, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, worldX) == 0x4c, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, worldY) == 0x50, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, hitPeer) == 0x74, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, contactPeer) == 0x7c, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, unknown_0xd0) == 0xd0, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, unknown_0xd4) == 0xd4, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, unknown_0xd8) == 0xd8, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, damage) == 0x104, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, health) == 0x10c, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, hitLeft) == 0x128, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, hitTop) == 0x12c, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, hitRight) == 0x130, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, hitBottom) == 0x134, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, attackLeft) == 0x138, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, attackTop) == 0x13c, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, attackRight) == 0x140, "level_one_actor_storage_02 original field");
static_assert(offsetof(ActorInteractionPrefixLayout, attackBottom) == 0x144, "level_one_actor_storage_02 original field");
struct InteractionRectangleLayout {
    uint32_t left;
    uint32_t top;
    uint32_t right;
    uint32_t bottom;
};
static_assert(std::is_standard_layout<InteractionRectangleLayout>::value, "layout contract");
static_assert(sizeof(InteractionRectangleLayout) == 0x10 && alignof(InteractionRectangleLayout) == 4, "v1.0 observed interaction prefix");
static_assert(offsetof(InteractionRectangleLayout, left) == 0x0, "level_one_actor_storage_02 original field");
static_assert(offsetof(InteractionRectangleLayout, top) == 0x4, "level_one_actor_storage_02 original field");
static_assert(offsetof(InteractionRectangleLayout, right) == 0x8, "level_one_actor_storage_02 original field");
static_assert(offsetof(InteractionRectangleLayout, bottom) == 0xc, "level_one_actor_storage_02 original field");
struct ProjectionPrefixLayout {
    uint8_t unknown_before_0x8[0x8];
    uint32_t flags;
    uint8_t unknown_before_0x30[0x24];
    uint32_t extentX;
    uint32_t extentY;
    uint8_t unknown_before_0x40[0x8];
    uint32_t cameraX;
    uint32_t cameraY;
    uint32_t visibleEndX;
    uint32_t visibleEndY;
    uint32_t screenOffsetX;
    uint32_t screenOffsetY;
};
static_assert(std::is_standard_layout<ProjectionPrefixLayout>::value, "layout contract");
static_assert(sizeof(ProjectionPrefixLayout) == 0x58 && alignof(ProjectionPrefixLayout) == 4, "v1.0 observed interaction prefix");
static_assert(offsetof(ProjectionPrefixLayout, flags) == 0x8, "level_one_actor_storage_02 original field");
static_assert(offsetof(ProjectionPrefixLayout, extentX) == 0x30, "level_one_actor_storage_02 original field");
static_assert(offsetof(ProjectionPrefixLayout, extentY) == 0x34, "level_one_actor_storage_02 original field");
static_assert(offsetof(ProjectionPrefixLayout, cameraX) == 0x40, "level_one_actor_storage_02 original field");
static_assert(offsetof(ProjectionPrefixLayout, cameraY) == 0x44, "level_one_actor_storage_02 original field");
static_assert(offsetof(ProjectionPrefixLayout, visibleEndX) == 0x48, "level_one_actor_storage_02 original field");
static_assert(offsetof(ProjectionPrefixLayout, visibleEndY) == 0x4c, "level_one_actor_storage_02 original field");
static_assert(offsetof(ProjectionPrefixLayout, screenOffsetX) == 0x50, "level_one_actor_storage_02 original field");
static_assert(offsetof(ProjectionPrefixLayout, screenOffsetY) == 0x54, "level_one_actor_storage_02 original field");
struct SurfaceUpdateScenePrefixLayout {
    uint8_t unknown_before_0xc[0xc];
    uint32_t configuration;
    uint32_t secondaryOwner;
    uint32_t primaryOwner;
};
static_assert(std::is_standard_layout<SurfaceUpdateScenePrefixLayout>::value, "layout contract");
static_assert(sizeof(SurfaceUpdateScenePrefixLayout) == 0x18 && alignof(SurfaceUpdateScenePrefixLayout) == 4, "v1.0 observed interaction prefix");
static_assert(offsetof(SurfaceUpdateScenePrefixLayout, configuration) == 0xc, "level_one_actor_storage_02 original field");
static_assert(offsetof(SurfaceUpdateScenePrefixLayout, secondaryOwner) == 0x10, "level_one_actor_storage_02 original field");
static_assert(offsetof(SurfaceUpdateScenePrefixLayout, primaryOwner) == 0x14, "level_one_actor_storage_02 original field");
struct SurfaceOwnerPrefixLayout {
    uint8_t unknown_before_0x2c[0x2c];
    uint32_t surface;
};
static_assert(std::is_standard_layout<SurfaceOwnerPrefixLayout>::value, "layout contract");
static_assert(sizeof(SurfaceOwnerPrefixLayout) == 0x30 && alignof(SurfaceOwnerPrefixLayout) == 4, "v1.0 observed interaction prefix");
static_assert(offsetof(SurfaceOwnerPrefixLayout, surface) == 0x2c, "level_one_actor_storage_02 original field");
struct SurfaceUpdateConfigurationPrefixLayout {
    uint8_t unknown_before_0x34[0x34];
    uint8_t flags;
};
static_assert(std::is_standard_layout<SurfaceUpdateConfigurationPrefixLayout>::value, "layout contract");
static_assert(sizeof(SurfaceUpdateConfigurationPrefixLayout) == 0x35 && alignof(SurfaceUpdateConfigurationPrefixLayout) == 1, "v1.0 observed interaction prefix");
static_assert(offsetof(SurfaceUpdateConfigurationPrefixLayout, flags) == 0x34, "level_one_actor_storage_02 original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class InteractionCallbackFields {
  public:
    InteractionCallbackFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(function, offsetof(InteractionCallbackPrefixLayout, function))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ActorInteractionFields {
  public:
    ActorInteractionFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(ActorInteractionPrefixLayout, flags))
    CLAW_RECOVERED_FIELD(worldX, offsetof(ActorInteractionPrefixLayout, worldX))
    CLAW_RECOVERED_FIELD(worldY, offsetof(ActorInteractionPrefixLayout, worldY))
    CLAW_RECOVERED_FIELD(hitPeer, offsetof(ActorInteractionPrefixLayout, hitPeer))
    CLAW_RECOVERED_FIELD(contactPeer, offsetof(ActorInteractionPrefixLayout, contactPeer))
    CLAW_RECOVERED_FIELD(unknown_0xd0, offsetof(ActorInteractionPrefixLayout, unknown_0xd0))
    CLAW_RECOVERED_FIELD(unknown_0xd4, offsetof(ActorInteractionPrefixLayout, unknown_0xd4))
    CLAW_RECOVERED_FIELD(unknown_0xd8, offsetof(ActorInteractionPrefixLayout, unknown_0xd8))
    CLAW_RECOVERED_FIELD(damage, offsetof(ActorInteractionPrefixLayout, damage))
    CLAW_RECOVERED_FIELD(health, offsetof(ActorInteractionPrefixLayout, health))
    CLAW_RECOVERED_FIELD(hitLeft, offsetof(ActorInteractionPrefixLayout, hitLeft))
    CLAW_RECOVERED_FIELD(hitTop, offsetof(ActorInteractionPrefixLayout, hitTop))
    CLAW_RECOVERED_FIELD(hitRight, offsetof(ActorInteractionPrefixLayout, hitRight))
    CLAW_RECOVERED_FIELD(hitBottom, offsetof(ActorInteractionPrefixLayout, hitBottom))
    CLAW_RECOVERED_FIELD(attackLeft, offsetof(ActorInteractionPrefixLayout, attackLeft))
    CLAW_RECOVERED_FIELD(attackTop, offsetof(ActorInteractionPrefixLayout, attackTop))
    CLAW_RECOVERED_FIELD(attackRight, offsetof(ActorInteractionPrefixLayout, attackRight))
    CLAW_RECOVERED_FIELD(attackBottom, offsetof(ActorInteractionPrefixLayout, attackBottom))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class InteractionRectangleFields {
  public:
    InteractionRectangleFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(left, offsetof(InteractionRectangleLayout, left))
    CLAW_RECOVERED_FIELD(top, offsetof(InteractionRectangleLayout, top))
    CLAW_RECOVERED_FIELD(right, offsetof(InteractionRectangleLayout, right))
    CLAW_RECOVERED_FIELD(bottom, offsetof(InteractionRectangleLayout, bottom))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ProjectionFields {
  public:
    ProjectionFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(ProjectionPrefixLayout, flags))
    CLAW_RECOVERED_FIELD(extentX, offsetof(ProjectionPrefixLayout, extentX))
    CLAW_RECOVERED_FIELD(extentY, offsetof(ProjectionPrefixLayout, extentY))
    CLAW_RECOVERED_FIELD(cameraX, offsetof(ProjectionPrefixLayout, cameraX))
    CLAW_RECOVERED_FIELD(cameraY, offsetof(ProjectionPrefixLayout, cameraY))
    CLAW_RECOVERED_FIELD(visibleEndX, offsetof(ProjectionPrefixLayout, visibleEndX))
    CLAW_RECOVERED_FIELD(visibleEndY, offsetof(ProjectionPrefixLayout, visibleEndY))
    CLAW_RECOVERED_FIELD(screenOffsetX, offsetof(ProjectionPrefixLayout, screenOffsetX))
    CLAW_RECOVERED_FIELD(screenOffsetY, offsetof(ProjectionPrefixLayout, screenOffsetY))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class SurfaceUpdateSceneFields {
  public:
    SurfaceUpdateSceneFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(configuration, offsetof(SurfaceUpdateScenePrefixLayout, configuration))
    CLAW_RECOVERED_FIELD(secondaryOwner, offsetof(SurfaceUpdateScenePrefixLayout, secondaryOwner))
    CLAW_RECOVERED_FIELD(primaryOwner, offsetof(SurfaceUpdateScenePrefixLayout, primaryOwner))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class SurfaceOwnerFields {
  public:
    SurfaceOwnerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(surface, offsetof(SurfaceOwnerPrefixLayout, surface))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint8_t Name() const { \
        return memory_.get8(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    }

template<class Memory> class ActorFlagByteFields {
  public:
    ActorFlagByteFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(ActorInteractionPrefixLayout, flags))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ProjectionFlagByteFields {
  public:
    ProjectionFlagByteFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(ProjectionPrefixLayout, flags))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class SurfaceUpdateConfigurationFields {
  public:
    SurfaceUpdateConfigurationFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(SurfaceUpdateConfigurationPrefixLayout, flags))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD
// Collision dispatch observes only these prefixes, not complete allocation sizes.
// The 0x80 word is passed to a collision callee; its broader role is unproven.
struct CollisionActorPrefixLayout {
    uint8_t unknown_before_0x80[0x80];
    uint32_t unknown_0x80;
    uint8_t unknown_before_0xcc[0x48];
    uint32_t motionState;
    uint8_t unknown_before_0xdc[0xc];
    uint32_t horizontalProbeStep;
    uint32_t verticalProbeStep;
    uint8_t unknown_before_0x118[0x34];
    uint32_t leftProbeOffset;
    uint32_t probeOffset_0x11c;
    uint32_t rightProbeOffset;
    uint32_t probeOffset_0x124;
};
static_assert(std::is_standard_layout<CollisionActorPrefixLayout>::value, "layout contract");
static_assert(sizeof(CollisionActorPrefixLayout) == 0x128 && alignof(CollisionActorPrefixLayout) == 4, "v1.0 observed collision actor prefix");
static_assert(offsetof(CollisionActorPrefixLayout, unknown_0x80) == 0x80, "0x4cbfaa");
static_assert(offsetof(CollisionActorPrefixLayout, motionState) == 0xcc, "0x4cbcd9 / 0x4cbf8f");
static_assert(offsetof(CollisionActorPrefixLayout, probeOffset_0x11c) == 0x11c, "0x4cbea1");
static_assert(offsetof(CollisionActorPrefixLayout, probeOffset_0x124) == 0x124, "0x4cbf1b");

struct CollisionManagerPrefixLayout {
    uint8_t unknown_before_0xc[0xc];
    uint32_t unknown_0xc;
    uint8_t unknown_before_0x4c[0x3c];
    uint32_t tileTypes;
    uint8_t unknown_before_0x5c[0xc];
    uint32_t tilePlane;
    uint8_t unknown_before_0x64[0x4];
    uint32_t horizontalStepLimit;
    uint32_t verticalStepLimit;
};
static_assert(std::is_standard_layout<CollisionManagerPrefixLayout>::value, "layout contract");
static_assert(sizeof(CollisionManagerPrefixLayout) == 0x6c && alignof(CollisionManagerPrefixLayout) == 4, "v1.0 observed collision manager prefix");
static_assert(offsetof(CollisionManagerPrefixLayout, horizontalStepLimit) == 0x64, "0x4cbb65");
static_assert(offsetof(CollisionManagerPrefixLayout, verticalStepLimit) == 0x68, "0x4cbba0 / 0x4cbc15");


// Tile plane words are loaded as uint32_t, with signed pixel comparisons and
// x86 shift-count masking performed at each original use in the runtime.
struct CollisionTilePlanePrefixLayout {
    uint8_t unknown_before_0x20[0x20];
    uint32_t tileIds;
    uint32_t rowOffsets;
    uint8_t unknown_before_0x30[0x8];
    uint32_t widthPixels;
    uint32_t heightPixels;
    uint8_t unknown_before_0x8c[0x54];
    uint32_t columnShift;
    uint32_t rowShift;
};
static_assert(std::is_standard_layout<CollisionTilePlanePrefixLayout>::value, "layout contract");
static_assert(sizeof(CollisionTilePlanePrefixLayout) == 0x94 && alignof(CollisionTilePlanePrefixLayout) == 4, "v1.0 observed tile-plane prefix");
static_assert(offsetof(CollisionActorPrefixLayout, horizontalProbeStep) == 0xdc, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionActorPrefixLayout, verticalProbeStep) == 0xe0, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionActorPrefixLayout, leftProbeOffset) == 0x118, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionActorPrefixLayout, rightProbeOffset) == 0x120, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionManagerPrefixLayout, unknown_0xc) == 0xc, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionManagerPrefixLayout, tileTypes) == 0x4c, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionManagerPrefixLayout, tilePlane) == 0x5c, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionTilePlanePrefixLayout, tileIds) == 0x20, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionTilePlanePrefixLayout, rowOffsets) == 0x24, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionTilePlanePrefixLayout, widthPixels) == 0x30, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionTilePlanePrefixLayout, heightPixels) == 0x34, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionTilePlanePrefixLayout, columnShift) == 0x8c, "level_one_collision_dispatch_02 original field");
static_assert(offsetof(CollisionTilePlanePrefixLayout, rowShift) == 0x90, "level_one_collision_dispatch_02 original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class CollisionActorFields {
  public:
    CollisionActorFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x80, offsetof(CollisionActorPrefixLayout, unknown_0x80))
    CLAW_RECOVERED_FIELD(horizontalProbeStep, offsetof(CollisionActorPrefixLayout, horizontalProbeStep))
    CLAW_RECOVERED_FIELD(verticalProbeStep, offsetof(CollisionActorPrefixLayout, verticalProbeStep))
    CLAW_RECOVERED_FIELD(leftProbeOffset, offsetof(CollisionActorPrefixLayout, leftProbeOffset))
    CLAW_RECOVERED_FIELD(rightProbeOffset, offsetof(CollisionActorPrefixLayout, rightProbeOffset))
    CLAW_RECOVERED_FIELD(motionState, offsetof(CollisionActorPrefixLayout, motionState))
    CLAW_RECOVERED_FIELD(probeOffset_0x11c, offsetof(CollisionActorPrefixLayout, probeOffset_0x11c))
    CLAW_RECOVERED_FIELD(probeOffset_0x124, offsetof(CollisionActorPrefixLayout, probeOffset_0x124))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class CollisionManagerFields {
  public:
    CollisionManagerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0xc, offsetof(CollisionManagerPrefixLayout, unknown_0xc))
    CLAW_RECOVERED_FIELD(tileTypes, offsetof(CollisionManagerPrefixLayout, tileTypes))
    CLAW_RECOVERED_FIELD(tilePlane, offsetof(CollisionManagerPrefixLayout, tilePlane))
    CLAW_RECOVERED_FIELD(horizontalStepLimit, offsetof(CollisionManagerPrefixLayout, horizontalStepLimit))
    CLAW_RECOVERED_FIELD(verticalStepLimit, offsetof(CollisionManagerPrefixLayout, verticalStepLimit))
  private:
    Memory &memory_;
    uint32_t token_;
};


template<class Memory> class CollisionTilePlaneFields {
  public:
    CollisionTilePlaneFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(tileIds, offsetof(CollisionTilePlanePrefixLayout, tileIds))
    CLAW_RECOVERED_FIELD(rowOffsets, offsetof(CollisionTilePlanePrefixLayout, rowOffsets))
    CLAW_RECOVERED_FIELD(widthPixels, offsetof(CollisionTilePlanePrefixLayout, widthPixels))
    CLAW_RECOVERED_FIELD(heightPixels, offsetof(CollisionTilePlanePrefixLayout, heightPixels))
    CLAW_RECOVERED_FIELD(columnShift, offsetof(CollisionTilePlanePrefixLayout, columnShift))
    CLAW_RECOVERED_FIELD(rowShift, offsetof(CollisionTilePlanePrefixLayout, rowShift))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

// World/tile collision layouts observed by level_one_world_collision_03.
// Contracts describe byte positions only; no object is overlaid on guest memory.

struct WorldLayerLayout {
    uint32_t vtable;
    uint32_t unknown_0x4;
    uint32_t flags;
    uint32_t resourceOwner;
    uint32_t scrollXBits;
    uint32_t scrollYBits;
    uint32_t scrollScaleXBits;
    uint32_t scrollScaleYBits;
    uint32_t tileIds;
    uint32_t rowOffsets;
    uint32_t columnCount;
    uint32_t rowCount;
    uint32_t widthPixels;
    uint32_t heightPixels;
    uint32_t tileWidth;
    uint32_t tileHeight;
    uint8_t unknown_before_0x50[0x10];
    uint32_t clipLeft;
    uint32_t clipTop;
    uint32_t clipRight;
    uint32_t clipBottom;
    uint32_t gridLeft;
    uint32_t gridTop;
    uint32_t gridRight;
    uint32_t gridBottom;
    uint32_t clipWidth;
    uint32_t clipHeight;
    uint32_t clipHalfWidth;
    uint32_t clipHalfHeight;
    uint32_t unknown_0x80;
    uint8_t unknown_before_0x8c[0x8];
    uint32_t columnShift;
    uint32_t rowShift;
    uint32_t scrollPercentX;
    uint32_t scrollPercentY;
    uint32_t unknown_0x9c;
    uint32_t resourceSlotData;
    uint32_t resourceSlotCount;
    uint8_t unknown_before_0xb0[0x8];
    uint32_t unknown_0xb0;
    uint8_t name[0x40];
    uint32_t unknown_0xf4;
    uint8_t unknown_before_0x144[0x4c];
    uint32_t unknown_0x144;
    uint8_t unknown_after_0x148[0x10];
};
static_assert(std::is_standard_layout<WorldLayerLayout>::value, "v1.0 world layout");
static_assert(sizeof(WorldLayerLayout) == 0x158 && alignof(WorldLayerLayout) == 4, "v1.0 observed world prefix");
static_assert(offsetof(WorldLayerLayout, vtable) == 0x0, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, unknown_0x4) == 0x4, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, flags) == 0x8, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, resourceOwner) == 0xc, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, scrollXBits) == 0x10, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, scrollYBits) == 0x14, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, scrollScaleXBits) == 0x18, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, scrollScaleYBits) == 0x1c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, tileIds) == 0x20, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, rowOffsets) == 0x24, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, columnCount) == 0x28, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, rowCount) == 0x2c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, widthPixels) == 0x30, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, heightPixels) == 0x34, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, tileWidth) == 0x38, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, tileHeight) == 0x3c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, clipLeft) == 0x50, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, clipTop) == 0x54, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, clipRight) == 0x58, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, clipBottom) == 0x5c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, gridLeft) == 0x60, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, gridTop) == 0x64, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, gridRight) == 0x68, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, gridBottom) == 0x6c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, clipWidth) == 0x70, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, clipHeight) == 0x74, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, clipHalfWidth) == 0x78, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, clipHalfHeight) == 0x7c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, unknown_0x80) == 0x80, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, columnShift) == 0x8c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, rowShift) == 0x90, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, scrollPercentX) == 0x94, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, scrollPercentY) == 0x98, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, unknown_0x9c) == 0x9c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, resourceSlotData) == 0xa0, "0x4d05ce");
static_assert(offsetof(WorldLayerLayout, resourceSlotCount) == 0xa4, "0x4d05c4");
static_assert(offsetof(WorldLayerLayout, unknown_0xb0) == 0xb0, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, name) == 0xb4, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, unknown_0xf4) == 0xf4, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerLayout, unknown_0x144) == 0x144, "level_one_world_collision_03 original field");

struct WorldLayerRecordLayout {
    uint32_t unknown_0x0;
    uint8_t unknown_before_0x8[0x4];
    uint32_t flags;
    uint8_t unknown_before_0x10[0x4];
    uint8_t name[0x40];
    uint8_t unknown_before_0x58[0x8];
    uint32_t tileWidth;
    uint32_t tileHeight;
    uint32_t columnCount;
    uint32_t rowCount;
    uint32_t startX;
    uint32_t startY;
    uint32_t scrollPercentX;
    uint32_t scrollPercentY;
    uint32_t unknown_0x78;
    uint32_t resourceNameCount;
    uint32_t extraCount;
    uint32_t tileDataOffset;
    uint32_t resourceNamesOffset;
    uint32_t extraOffset;
    uint32_t unknown_0x90;
};
static_assert(std::is_standard_layout<WorldLayerRecordLayout>::value, "v1.0 world layout");
static_assert(sizeof(WorldLayerRecordLayout) == 0x94 && alignof(WorldLayerRecordLayout) == 4, "v1.0 observed world prefix");
static_assert(offsetof(WorldLayerRecordLayout, unknown_0x0) == 0x0, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, flags) == 0x8, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, name) == 0x10, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, tileWidth) == 0x58, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, tileHeight) == 0x5c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, columnCount) == 0x60, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, rowCount) == 0x64, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, startX) == 0x68, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, startY) == 0x6c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, scrollPercentX) == 0x70, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, scrollPercentY) == 0x74, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, unknown_0x78) == 0x78, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, resourceNameCount) == 0x7c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, extraCount) == 0x80, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, tileDataOffset) == 0x84, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, resourceNamesOffset) == 0x88, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, extraOffset) == 0x8c, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerRecordLayout, unknown_0x90) == 0x90, "level_one_world_collision_03 original field");

struct TileRectangleHandlerLayout {
    uint8_t unknown_before_0xc[0xc];
    uint32_t outsideResponse;
    uint32_t insideResponse;
    uint32_t left;
    uint32_t top;
    uint32_t right;
    uint32_t bottom;
};
static_assert(std::is_standard_layout<TileRectangleHandlerLayout>::value, "v1.0 world layout");
static_assert(sizeof(TileRectangleHandlerLayout) == 0x24 && alignof(TileRectangleHandlerLayout) == 4, "v1.0 observed world prefix");
static_assert(offsetof(TileRectangleHandlerLayout, outsideResponse) == 0xc, "level_one_world_collision_03 original field");
static_assert(offsetof(TileRectangleHandlerLayout, insideResponse) == 0x10, "level_one_world_collision_03 original field");
static_assert(offsetof(TileRectangleHandlerLayout, left) == 0x14, "level_one_world_collision_03 original field");
static_assert(offsetof(TileRectangleHandlerLayout, top) == 0x18, "level_one_world_collision_03 original field");
static_assert(offsetof(TileRectangleHandlerLayout, right) == 0x1c, "level_one_world_collision_03 original field");
static_assert(offsetof(TileRectangleHandlerLayout, bottom) == 0x20, "level_one_world_collision_03 original field");

struct WorldLayerCollectionLayout {
    uint8_t unknown_before_0x38[0x38];
    uint32_t layers;
    uint32_t layerCount;
};
static_assert(std::is_standard_layout<WorldLayerCollectionLayout>::value, "v1.0 world layout");
static_assert(sizeof(WorldLayerCollectionLayout) == 0x40 && alignof(WorldLayerCollectionLayout) == 4, "v1.0 observed world prefix");
static_assert(offsetof(WorldLayerCollectionLayout, layers) == 0x38, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldLayerCollectionLayout, layerCount) == 0x3c, "level_one_world_collision_03 original field");

struct WorldResourceOwnerLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t lookupOwner;
};
static_assert(std::is_standard_layout<WorldResourceOwnerLayout>::value, "v1.0 world layout");
static_assert(sizeof(WorldResourceOwnerLayout) == 0x14 && alignof(WorldResourceOwnerLayout) == 4, "v1.0 observed world prefix");
static_assert(offsetof(WorldResourceOwnerLayout, lookupOwner) == 0x10, "level_one_world_collision_03 original field");

struct WorldResourceListLayout {
    uint8_t unknown_before_0x14[0x14];
    uint32_t items;
    uint32_t count;
    uint8_t unknown_before_0x64[0x48];
    uint32_t firstIndex;
    uint32_t lastIndex;
};
static_assert(std::is_standard_layout<WorldResourceListLayout>::value, "v1.0 world layout");
static_assert(sizeof(WorldResourceListLayout) == 0x6c && alignof(WorldResourceListLayout) == 4, "v1.0 observed world prefix");
static_assert(offsetof(WorldResourceListLayout, items) == 0x14, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldResourceListLayout, count) == 0x18, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldResourceListLayout, firstIndex) == 0x64, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldResourceListLayout, lastIndex) == 0x68, "level_one_world_collision_03 original field");

struct WorldResourceDimensionsLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t tileWidth;
    uint32_t tileHeight;
};
static_assert(std::is_standard_layout<WorldResourceDimensionsLayout>::value, "v1.0 world layout");
static_assert(sizeof(WorldResourceDimensionsLayout) == 0x18 && alignof(WorldResourceDimensionsLayout) == 4, "v1.0 observed world prefix");
static_assert(offsetof(WorldResourceDimensionsLayout, tileWidth) == 0x10, "level_one_world_collision_03 original field");
static_assert(offsetof(WorldResourceDimensionsLayout, tileHeight) == 0x14, "level_one_world_collision_03 original field");

// One word of the constructor's 25-word trailing clear range.
struct WorldLayerTrailingWordLayout {
    uint32_t value;
};
static_assert(std::is_standard_layout<WorldLayerTrailingWordLayout>::value, "v1.0 trailing clear word");
static_assert(sizeof(WorldLayerTrailingWordLayout) == 4 && alignof(WorldLayerTrailingWordLayout) == 4, "v1.0 trailing clear word");
static_assert(offsetof(WorldLayerTrailingWordLayout, value) == 0, "0x4d042d rep stosd");

struct GridElementLayout {
    uint32_t unknown_0x0;
    uint32_t unknown_0x4;
};
static_assert(std::is_standard_layout<GridElementLayout>::value, "v1.0 world layout");
static_assert(sizeof(GridElementLayout) == 0x8 && alignof(GridElementLayout) == 4, "v1.0 observed world prefix");
static_assert(offsetof(GridElementLayout, unknown_0x0) == 0x0, "level_one_world_collision_03 original field");
static_assert(offsetof(GridElementLayout, unknown_0x4) == 0x4, "level_one_world_collision_03 original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class WorldLayerFields {
  public:
    WorldLayerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(vtable, offsetof(WorldLayerLayout, vtable))
    CLAW_RECOVERED_FIELD(unknown_0x4, offsetof(WorldLayerLayout, unknown_0x4))
    CLAW_RECOVERED_FIELD(flags, offsetof(WorldLayerLayout, flags))
    CLAW_RECOVERED_FIELD(resourceOwner, offsetof(WorldLayerLayout, resourceOwner))
    CLAW_RECOVERED_FIELD(scrollXBits, offsetof(WorldLayerLayout, scrollXBits))
    CLAW_RECOVERED_FIELD(scrollYBits, offsetof(WorldLayerLayout, scrollYBits))
    CLAW_RECOVERED_FIELD(scrollScaleXBits, offsetof(WorldLayerLayout, scrollScaleXBits))
    CLAW_RECOVERED_FIELD(scrollScaleYBits, offsetof(WorldLayerLayout, scrollScaleYBits))
    CLAW_RECOVERED_FIELD(tileIds, offsetof(WorldLayerLayout, tileIds))
    CLAW_RECOVERED_FIELD(rowOffsets, offsetof(WorldLayerLayout, rowOffsets))
    CLAW_RECOVERED_FIELD(columnCount, offsetof(WorldLayerLayout, columnCount))
    CLAW_RECOVERED_FIELD(rowCount, offsetof(WorldLayerLayout, rowCount))
    CLAW_RECOVERED_FIELD(widthPixels, offsetof(WorldLayerLayout, widthPixels))
    CLAW_RECOVERED_FIELD(heightPixels, offsetof(WorldLayerLayout, heightPixels))
    CLAW_RECOVERED_FIELD(tileWidth, offsetof(WorldLayerLayout, tileWidth))
    CLAW_RECOVERED_FIELD(tileHeight, offsetof(WorldLayerLayout, tileHeight))
    CLAW_RECOVERED_FIELD(clipLeft, offsetof(WorldLayerLayout, clipLeft))
    CLAW_RECOVERED_FIELD(clipTop, offsetof(WorldLayerLayout, clipTop))
    CLAW_RECOVERED_FIELD(clipRight, offsetof(WorldLayerLayout, clipRight))
    CLAW_RECOVERED_FIELD(clipBottom, offsetof(WorldLayerLayout, clipBottom))
    CLAW_RECOVERED_FIELD(gridLeft, offsetof(WorldLayerLayout, gridLeft))
    CLAW_RECOVERED_FIELD(gridTop, offsetof(WorldLayerLayout, gridTop))
    CLAW_RECOVERED_FIELD(gridRight, offsetof(WorldLayerLayout, gridRight))
    CLAW_RECOVERED_FIELD(gridBottom, offsetof(WorldLayerLayout, gridBottom))
    CLAW_RECOVERED_FIELD(clipWidth, offsetof(WorldLayerLayout, clipWidth))
    CLAW_RECOVERED_FIELD(clipHeight, offsetof(WorldLayerLayout, clipHeight))
    CLAW_RECOVERED_FIELD(clipHalfWidth, offsetof(WorldLayerLayout, clipHalfWidth))
    CLAW_RECOVERED_FIELD(clipHalfHeight, offsetof(WorldLayerLayout, clipHalfHeight))
    CLAW_RECOVERED_FIELD(unknown_0x80, offsetof(WorldLayerLayout, unknown_0x80))
    CLAW_RECOVERED_FIELD(columnShift, offsetof(WorldLayerLayout, columnShift))
    CLAW_RECOVERED_FIELD(rowShift, offsetof(WorldLayerLayout, rowShift))
    CLAW_RECOVERED_FIELD(scrollPercentX, offsetof(WorldLayerLayout, scrollPercentX))
    CLAW_RECOVERED_FIELD(scrollPercentY, offsetof(WorldLayerLayout, scrollPercentY))
    CLAW_RECOVERED_FIELD(unknown_0xb0, offsetof(WorldLayerLayout, unknown_0xb0))
    CLAW_RECOVERED_FIELD(unknown_0xf4, offsetof(WorldLayerLayout, unknown_0xf4))
    CLAW_RECOVERED_FIELD(unknown_0x144, offsetof(WorldLayerLayout, unknown_0x144))
    CLAW_RECOVERED_FIELD(resourceSlotData, offsetof(WorldLayerLayout, resourceSlotData))
    CLAW_RECOVERED_FIELD(resourceSlotCount, offsetof(WorldLayerLayout, resourceSlotCount))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class WorldLayerRecordFields {
  public:
    WorldLayerRecordFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x0, offsetof(WorldLayerRecordLayout, unknown_0x0))
    CLAW_RECOVERED_FIELD(flags, offsetof(WorldLayerRecordLayout, flags))
    CLAW_RECOVERED_FIELD(tileWidth, offsetof(WorldLayerRecordLayout, tileWidth))
    CLAW_RECOVERED_FIELD(tileHeight, offsetof(WorldLayerRecordLayout, tileHeight))
    CLAW_RECOVERED_FIELD(columnCount, offsetof(WorldLayerRecordLayout, columnCount))
    CLAW_RECOVERED_FIELD(rowCount, offsetof(WorldLayerRecordLayout, rowCount))
    CLAW_RECOVERED_FIELD(startX, offsetof(WorldLayerRecordLayout, startX))
    CLAW_RECOVERED_FIELD(startY, offsetof(WorldLayerRecordLayout, startY))
    CLAW_RECOVERED_FIELD(scrollPercentX, offsetof(WorldLayerRecordLayout, scrollPercentX))
    CLAW_RECOVERED_FIELD(scrollPercentY, offsetof(WorldLayerRecordLayout, scrollPercentY))
    CLAW_RECOVERED_FIELD(unknown_0x78, offsetof(WorldLayerRecordLayout, unknown_0x78))
    CLAW_RECOVERED_FIELD(resourceNameCount, offsetof(WorldLayerRecordLayout, resourceNameCount))
    CLAW_RECOVERED_FIELD(extraCount, offsetof(WorldLayerRecordLayout, extraCount))
    CLAW_RECOVERED_FIELD(tileDataOffset, offsetof(WorldLayerRecordLayout, tileDataOffset))
    CLAW_RECOVERED_FIELD(resourceNamesOffset, offsetof(WorldLayerRecordLayout, resourceNamesOffset))
    CLAW_RECOVERED_FIELD(extraOffset, offsetof(WorldLayerRecordLayout, extraOffset))
    CLAW_RECOVERED_FIELD(unknown_0x90, offsetof(WorldLayerRecordLayout, unknown_0x90))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class TileRectangleHandlerFields {
  public:
    TileRectangleHandlerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(outsideResponse, offsetof(TileRectangleHandlerLayout, outsideResponse))
    CLAW_RECOVERED_FIELD(insideResponse, offsetof(TileRectangleHandlerLayout, insideResponse))
    CLAW_RECOVERED_FIELD(left, offsetof(TileRectangleHandlerLayout, left))
    CLAW_RECOVERED_FIELD(top, offsetof(TileRectangleHandlerLayout, top))
    CLAW_RECOVERED_FIELD(right, offsetof(TileRectangleHandlerLayout, right))
    CLAW_RECOVERED_FIELD(bottom, offsetof(TileRectangleHandlerLayout, bottom))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class WorldLayerCollectionFields {
  public:
    WorldLayerCollectionFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(layers, offsetof(WorldLayerCollectionLayout, layers))
    CLAW_RECOVERED_FIELD(layerCount, offsetof(WorldLayerCollectionLayout, layerCount))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class WorldResourceOwnerFields {
  public:
    WorldResourceOwnerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(lookupOwner, offsetof(WorldResourceOwnerLayout, lookupOwner))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class WorldResourceListFields {
  public:
    WorldResourceListFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(items, offsetof(WorldResourceListLayout, items))
    CLAW_RECOVERED_FIELD(count, offsetof(WorldResourceListLayout, count))
    CLAW_RECOVERED_FIELD(firstIndex, offsetof(WorldResourceListLayout, firstIndex))
    CLAW_RECOVERED_FIELD(lastIndex, offsetof(WorldResourceListLayout, lastIndex))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class WorldResourceDimensionsFields {
  public:
    WorldResourceDimensionsFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(tileWidth, offsetof(WorldResourceDimensionsLayout, tileWidth))
    CLAW_RECOVERED_FIELD(tileHeight, offsetof(WorldResourceDimensionsLayout, tileHeight))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class WorldLayerTrailingWordFields {
  public:
    WorldLayerTrailingWordFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(value, offsetof(WorldLayerTrailingWordLayout, value))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class GridElementFields {
  public:
    GridElementFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x0, offsetof(GridElementLayout, unknown_0x0))
    CLAW_RECOVERED_FIELD(unknown_0x4, offsetof(GridElementLayout, unknown_0x4))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint8_t Name() const { \
        return memory_.get8(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    }

template<class Memory> class WorldLayerFlagByteFields {
  public:
    WorldLayerFlagByteFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(WorldLayerLayout, flags))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

// End actor storage/collision chain.

} // namespace v10

namespace v13 {

// Observed application prefix only, never an overlay on guest storage.
struct ApplicationProfilePrefixLayout {
    uint8_t unknown_before_0x2c[0x2c];
    uint32_t modeProvider;
    uint8_t unknown_before_0x64[0x34];
    ProfileToken selectedProfile;
};

static_assert(sizeof(ApplicationToken) == 4 && alignof(ApplicationToken) == 4,
              "v1.3 application tokens remain 32-bit words");
static_assert(sizeof(ProfileToken) == 4 && alignof(ProfileToken) == 4,
              "v1.3 profile tokens remain 32-bit words");
static_assert(std::is_standard_layout<ApplicationProfilePrefixLayout>::value, "layout contract");
static_assert(sizeof(ApplicationProfilePrefixLayout) == 0x68 && alignof(ApplicationProfilePrefixLayout) == 4,
              "v1.3 observed application profile prefix");
static_assert(offsetof(ApplicationProfilePrefixLayout, modeProvider) == 0x2c, "0x42a923 / 0x42a930");
static_assert(offsetof(ApplicationProfilePrefixLayout, selectedProfile) == 0x64, "0x487af3");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class ApplicationProfileFields {
  public:
    ApplicationProfileFields(Memory &memory, ApplicationToken token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(modeProvider, offsetof(ApplicationProfilePrefixLayout, modeProvider))
    CLAW_RECOVERED_FIELD(selectedProfile, offsetof(ApplicationProfilePrefixLayout, selectedProfile))
  private:
    Memory &memory_;
    ApplicationToken token_;
};

#undef CLAW_RECOVERED_FIELD

// Version 1.3 movement prefixes observed by 0x416ee0 / 0x4194d0 / 0x4198a0.
// These contracts describe guest bytes only; views never overlay host structs.
struct MovementActorPrefixLayout {
    uint8_t unknown_before_0x8[0x8];
    uint32_t flags;
    uint32_t scene;
    uint8_t unknown_before_0x40[0x30];
    uint32_t unknown_0x40;
    uint8_t unknown_before_0x5c[0x18];
    uint32_t worldX;
    uint32_t worldY;
    uint8_t unknown_before_0x7c[0x18];
    uint32_t logicHolder;
    uint8_t unknown_before_0x98[0x18];
    uint32_t platform;
    uint8_t unknown_before_0xe4[0x48];
    uint32_t movementMode;
    uint32_t unknown_0xe8;
    uint32_t unknown_0xec;
    uint8_t unknown_before_0x110[0x20];
    uint32_t unknown_0x110;
    uint32_t unknown_0x114;
    uint8_t unknown_before_0x120[0x8];
    uint32_t unknown_0x120;
    uint8_t unknown_before_0x128[0x4];
    uint32_t health;
    uint8_t unknown_before_0x134[0x8];
    uint32_t hitLeft;
    uint8_t unknown_before_0x13c[0x4];
    uint32_t hitRight;
    uint8_t unknown_before_0x164[0x24];
    uint32_t horizontalSpeed;
    uint32_t verticalSpeed;
    uint8_t unknown_before_0x194[0x28];
    uint32_t animation;
    uint8_t unknown_before_0x1d8[0x40];
    uint32_t animationScaleBits;
};
static_assert(std::is_standard_layout<MovementActorPrefixLayout>::value, "v1.3 movement layout");
static_assert(sizeof(MovementActorPrefixLayout) == 0x1dc && alignof(MovementActorPrefixLayout) == 4, "v1.3 observed movement prefix");
static_assert(offsetof(MovementActorPrefixLayout, flags) == 0x8, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, scene) == 0xc, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, unknown_0x40) == 0x40, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, worldX) == 0x5c, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, worldY) == 0x60, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, logicHolder) == 0x7c, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, platform) == 0x98, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, movementMode) == 0xe4, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, unknown_0xe8) == 0xe8, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, unknown_0xec) == 0xec, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, unknown_0x110) == 0x110, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, unknown_0x114) == 0x114, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, unknown_0x120) == 0x120, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, health) == 0x128, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, hitLeft) == 0x134, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, hitRight) == 0x13c, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, horizontalSpeed) == 0x164, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, verticalSpeed) == 0x168, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, animation) == 0x194, "v1.3 movement original field");
static_assert(offsetof(MovementActorPrefixLayout, animationScaleBits) == 0x1d8, "v1.3 movement original field");

struct MovementHolderPrefixLayout {
    uint8_t unknown_before_0x14[0x14];
    uint32_t privateState;
    uint8_t unknown_before_0x1c[0x4];
    uint32_t mode;
    uint8_t unknown_before_0x2c[0xc];
    uint32_t minimumX;
    uint32_t maximumX;
    uint32_t minimumY;
    uint32_t maximumY;
    uint8_t unknown_before_0x130[0xf4];
    uint32_t unknown_0x130;
    uint8_t unknown_before_0x178[0x44];
    uint32_t privateStateBytes;
};
static_assert(std::is_standard_layout<MovementHolderPrefixLayout>::value, "v1.3 movement layout");
static_assert(sizeof(MovementHolderPrefixLayout) == 0x17c && alignof(MovementHolderPrefixLayout) == 4, "v1.3 observed movement prefix");
static_assert(offsetof(MovementHolderPrefixLayout, privateState) == 0x14, "v1.3 movement original field");
static_assert(offsetof(MovementHolderPrefixLayout, mode) == 0x1c, "v1.3 movement original field");
static_assert(offsetof(MovementHolderPrefixLayout, minimumX) == 0x2c, "v1.3 movement original field");
static_assert(offsetof(MovementHolderPrefixLayout, maximumX) == 0x30, "v1.3 movement original field");
static_assert(offsetof(MovementHolderPrefixLayout, minimumY) == 0x34, "v1.3 movement original field");
static_assert(offsetof(MovementHolderPrefixLayout, maximumY) == 0x38, "v1.3 movement original field");
static_assert(offsetof(MovementHolderPrefixLayout, unknown_0x130) == 0x130, "v1.3 movement original field");
static_assert(offsetof(MovementHolderPrefixLayout, privateStateBytes) == 0x178, "v1.3 movement original field");

struct MovementPrivatePrefixLayout {
    uint32_t unknown_0x0;
    uint32_t unknown_0x4;
    uint8_t unknown_before_0x18[0x10];
    uint32_t unknown_0x18;
    uint32_t unknown_0x1c;
    uint32_t unknown_0x20;
    uint32_t unknown_0x24;
    uint8_t unknown_before_0x2c[0x4];
    uint32_t unknown_0x2c;
    uint32_t weapon;
    uint8_t unknown_before_0x3c[0x8];
    uint32_t attackMode;
    uint32_t unknown_0x40;
    uint32_t unknown_0x44;
    uint32_t health;
    uint32_t spawnX;
    uint32_t spawnY;
    uint8_t unknown_before_0x5c[0x8];
    uint32_t unknown_0x5c;
    uint32_t jumpStartY;
    uint32_t jumpLimitY;
    uint8_t unknown_before_0x70[0x8];
    uint32_t unknown_0x70;
    uint32_t unknown_0x74;
    uint32_t unknown_0x78;
    uint32_t unknown_0x7c;
    uint8_t unknown_before_0x84[0x4];
    uint32_t speedAdjustment;
    uint8_t unknown_before_0xe8[0x60];
    uint32_t unknown_0xe8;
    uint8_t unknown_before_0xf8[0xc];
    uint32_t unknown_0xf8;
    uint32_t unknown_0xfc;
    uint8_t unknown_before_0x10c[0xc];
    uint32_t unknown_0x10c;
    uint32_t unknown_0x110;
    uint32_t accelerationCountdown;
    uint32_t unknown_0x118;
    uint32_t unknown_0x11c;
    uint32_t unknown_0x120;
    uint32_t retainedAnimation;
    uint32_t unknown_0x128;
    uint32_t speechActor;
    uint32_t unknown_0x130;
    uint32_t unknown_0x134;
};
static_assert(std::is_standard_layout<MovementPrivatePrefixLayout>::value, "v1.3 movement layout");
static_assert(sizeof(MovementPrivatePrefixLayout) == 0x138 && alignof(MovementPrivatePrefixLayout) == 4, "v1.3 observed movement prefix");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x0) == 0x0, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x4) == 0x4, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x18) == 0x18, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x1c) == 0x1c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x20) == 0x20, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x24) == 0x24, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x2c) == 0x2c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, weapon) == 0x30, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, attackMode) == 0x3c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x40) == 0x40, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x44) == 0x44, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, health) == 0x48, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, spawnX) == 0x4c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, spawnY) == 0x50, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x5c) == 0x5c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, jumpStartY) == 0x60, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, jumpLimitY) == 0x64, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x70) == 0x70, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x74) == 0x74, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x78) == 0x78, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x7c) == 0x7c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, speedAdjustment) == 0x84, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0xe8) == 0xe8, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0xf8) == 0xf8, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0xfc) == 0xfc, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x10c) == 0x10c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x110) == 0x110, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, accelerationCountdown) == 0x114, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x118) == 0x118, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x11c) == 0x11c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x120) == 0x120, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, retainedAnimation) == 0x124, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x128) == 0x128, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, speechActor) == 0x12c, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x130) == 0x130, "v1.3 movement original field");
static_assert(offsetof(MovementPrivatePrefixLayout, unknown_0x134) == 0x134, "v1.3 movement original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class MovementActorFields {
  public:
    MovementActorFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(MovementActorPrefixLayout, flags))
    CLAW_RECOVERED_FIELD(scene, offsetof(MovementActorPrefixLayout, scene))
    CLAW_RECOVERED_FIELD(unknown_0x40, offsetof(MovementActorPrefixLayout, unknown_0x40))
    CLAW_RECOVERED_FIELD(worldX, offsetof(MovementActorPrefixLayout, worldX))
    CLAW_RECOVERED_FIELD(worldY, offsetof(MovementActorPrefixLayout, worldY))
    CLAW_RECOVERED_FIELD(logicHolder, offsetof(MovementActorPrefixLayout, logicHolder))
    CLAW_RECOVERED_FIELD(platform, offsetof(MovementActorPrefixLayout, platform))
    CLAW_RECOVERED_FIELD(movementMode, offsetof(MovementActorPrefixLayout, movementMode))
    CLAW_RECOVERED_FIELD(unknown_0xe8, offsetof(MovementActorPrefixLayout, unknown_0xe8))
    CLAW_RECOVERED_FIELD(unknown_0xec, offsetof(MovementActorPrefixLayout, unknown_0xec))
    CLAW_RECOVERED_FIELD(unknown_0x110, offsetof(MovementActorPrefixLayout, unknown_0x110))
    CLAW_RECOVERED_FIELD(unknown_0x114, offsetof(MovementActorPrefixLayout, unknown_0x114))
    CLAW_RECOVERED_FIELD(unknown_0x120, offsetof(MovementActorPrefixLayout, unknown_0x120))
    CLAW_RECOVERED_FIELD(health, offsetof(MovementActorPrefixLayout, health))
    CLAW_RECOVERED_FIELD(hitLeft, offsetof(MovementActorPrefixLayout, hitLeft))
    CLAW_RECOVERED_FIELD(hitRight, offsetof(MovementActorPrefixLayout, hitRight))
    CLAW_RECOVERED_FIELD(horizontalSpeed, offsetof(MovementActorPrefixLayout, horizontalSpeed))
    CLAW_RECOVERED_FIELD(verticalSpeed, offsetof(MovementActorPrefixLayout, verticalSpeed))
    CLAW_RECOVERED_FIELD(animation, offsetof(MovementActorPrefixLayout, animation))
    CLAW_RECOVERED_FIELD(animationScaleBits, offsetof(MovementActorPrefixLayout, animationScaleBits))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class MovementHolderFields {
  public:
    MovementHolderFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(privateState, offsetof(MovementHolderPrefixLayout, privateState))
    CLAW_RECOVERED_FIELD(mode, offsetof(MovementHolderPrefixLayout, mode))
    CLAW_RECOVERED_FIELD(minimumX, offsetof(MovementHolderPrefixLayout, minimumX))
    CLAW_RECOVERED_FIELD(maximumX, offsetof(MovementHolderPrefixLayout, maximumX))
    CLAW_RECOVERED_FIELD(minimumY, offsetof(MovementHolderPrefixLayout, minimumY))
    CLAW_RECOVERED_FIELD(maximumY, offsetof(MovementHolderPrefixLayout, maximumY))
    CLAW_RECOVERED_FIELD(unknown_0x130, offsetof(MovementHolderPrefixLayout, unknown_0x130))
    CLAW_RECOVERED_FIELD(privateStateBytes, offsetof(MovementHolderPrefixLayout, privateStateBytes))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class MovementPrivateFields {
  public:
    MovementPrivateFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x0, offsetof(MovementPrivatePrefixLayout, unknown_0x0))
    CLAW_RECOVERED_FIELD(unknown_0x4, offsetof(MovementPrivatePrefixLayout, unknown_0x4))
    CLAW_RECOVERED_FIELD(unknown_0x18, offsetof(MovementPrivatePrefixLayout, unknown_0x18))
    CLAW_RECOVERED_FIELD(unknown_0x1c, offsetof(MovementPrivatePrefixLayout, unknown_0x1c))
    CLAW_RECOVERED_FIELD(unknown_0x20, offsetof(MovementPrivatePrefixLayout, unknown_0x20))
    CLAW_RECOVERED_FIELD(unknown_0x24, offsetof(MovementPrivatePrefixLayout, unknown_0x24))
    CLAW_RECOVERED_FIELD(unknown_0x2c, offsetof(MovementPrivatePrefixLayout, unknown_0x2c))
    CLAW_RECOVERED_FIELD(weapon, offsetof(MovementPrivatePrefixLayout, weapon))
    CLAW_RECOVERED_FIELD(attackMode, offsetof(MovementPrivatePrefixLayout, attackMode))
    CLAW_RECOVERED_FIELD(unknown_0x40, offsetof(MovementPrivatePrefixLayout, unknown_0x40))
    CLAW_RECOVERED_FIELD(unknown_0x44, offsetof(MovementPrivatePrefixLayout, unknown_0x44))
    CLAW_RECOVERED_FIELD(health, offsetof(MovementPrivatePrefixLayout, health))
    CLAW_RECOVERED_FIELD(spawnX, offsetof(MovementPrivatePrefixLayout, spawnX))
    CLAW_RECOVERED_FIELD(spawnY, offsetof(MovementPrivatePrefixLayout, spawnY))
    CLAW_RECOVERED_FIELD(unknown_0x5c, offsetof(MovementPrivatePrefixLayout, unknown_0x5c))
    CLAW_RECOVERED_FIELD(jumpStartY, offsetof(MovementPrivatePrefixLayout, jumpStartY))
    CLAW_RECOVERED_FIELD(jumpLimitY, offsetof(MovementPrivatePrefixLayout, jumpLimitY))
    CLAW_RECOVERED_FIELD(unknown_0x70, offsetof(MovementPrivatePrefixLayout, unknown_0x70))
    CLAW_RECOVERED_FIELD(unknown_0x74, offsetof(MovementPrivatePrefixLayout, unknown_0x74))
    CLAW_RECOVERED_FIELD(unknown_0x78, offsetof(MovementPrivatePrefixLayout, unknown_0x78))
    CLAW_RECOVERED_FIELD(unknown_0x7c, offsetof(MovementPrivatePrefixLayout, unknown_0x7c))
    CLAW_RECOVERED_FIELD(speedAdjustment, offsetof(MovementPrivatePrefixLayout, speedAdjustment))
    CLAW_RECOVERED_FIELD(unknown_0xe8, offsetof(MovementPrivatePrefixLayout, unknown_0xe8))
    CLAW_RECOVERED_FIELD(unknown_0xf8, offsetof(MovementPrivatePrefixLayout, unknown_0xf8))
    CLAW_RECOVERED_FIELD(unknown_0xfc, offsetof(MovementPrivatePrefixLayout, unknown_0xfc))
    CLAW_RECOVERED_FIELD(unknown_0x10c, offsetof(MovementPrivatePrefixLayout, unknown_0x10c))
    CLAW_RECOVERED_FIELD(unknown_0x110, offsetof(MovementPrivatePrefixLayout, unknown_0x110))
    CLAW_RECOVERED_FIELD(accelerationCountdown, offsetof(MovementPrivatePrefixLayout, accelerationCountdown))
    CLAW_RECOVERED_FIELD(unknown_0x118, offsetof(MovementPrivatePrefixLayout, unknown_0x118))
    CLAW_RECOVERED_FIELD(unknown_0x11c, offsetof(MovementPrivatePrefixLayout, unknown_0x11c))
    CLAW_RECOVERED_FIELD(unknown_0x120, offsetof(MovementPrivatePrefixLayout, unknown_0x120))
    CLAW_RECOVERED_FIELD(retainedAnimation, offsetof(MovementPrivatePrefixLayout, retainedAnimation))
    CLAW_RECOVERED_FIELD(unknown_0x128, offsetof(MovementPrivatePrefixLayout, unknown_0x128))
    CLAW_RECOVERED_FIELD(speechActor, offsetof(MovementPrivatePrefixLayout, speechActor))
    CLAW_RECOVERED_FIELD(unknown_0x130, offsetof(MovementPrivatePrefixLayout, unknown_0x130))
    CLAW_RECOVERED_FIELD(unknown_0x134, offsetof(MovementPrivatePrefixLayout, unknown_0x134))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

// Version 1.3 attack prefixes observed by the original entry 0x41f270.
// Separate from the movement prefixes: identical offsets alone do not prove
// that animation/private-state fields have the same meaning in every view.
// These are checked descriptions of bytes, never overlays on guest storage.
struct AttackActorPrefixLayout {
    uint8_t unknown_before_0x8[0x8];
    uint32_t flags;
    uint32_t scene;
    uint8_t unknown_before_0x7c[0x6c];
    uint32_t logicHolder;
    uint8_t unknown_before_0x120[0xa0];
    uint32_t damage;
    uint8_t unknown_before_0x154[0x30];
    uint32_t attackLeft;
    uint32_t attackTop;
    uint32_t attackRight;
    uint32_t attackBottom;
    uint8_t unknown_before_0x1b4[0x50];
    uint32_t savedAnimationSource;
};
static_assert(std::is_standard_layout<AttackActorPrefixLayout>::value, "v1.3 attack layout");
static_assert(sizeof(AttackActorPrefixLayout) == 0x1b8 && alignof(AttackActorPrefixLayout) == 4, "v1.3 observed attack prefix");
static_assert(offsetof(AttackActorPrefixLayout, flags) == 0x8, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackActorPrefixLayout, scene) == 0xc, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackActorPrefixLayout, logicHolder) == 0x7c, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackActorPrefixLayout, damage) == 0x120, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackActorPrefixLayout, attackLeft) == 0x154, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackActorPrefixLayout, attackTop) == 0x158, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackActorPrefixLayout, attackRight) == 0x15c, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackActorPrefixLayout, attackBottom) == 0x160, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackActorPrefixLayout, savedAnimationSource) == 0x1b4, "v1.3 0x41f270 original field");

struct AttackPrivatePrefixLayout {
    uint32_t facing;
    uint32_t active;
    uint8_t unknown_before_0x10[0x8];
    uint32_t unknown_0x10;
    uint32_t unknown_0x14;
    uint8_t unknown_before_0x1c[0x4];
    uint32_t animationPending;
    uint32_t cancelled;
    uint8_t unknown_before_0x3c[0x18];
    uint32_t attackId;
    uint8_t unknown_before_0x54[0x14];
    uint32_t unknown_0x54;
    uint32_t unknown_0x58;
    uint8_t unknown_before_0x6c[0x10];
    uint32_t weaponMode;
    uint32_t pistolAmmunition;
    uint32_t magicAmmunition;
    uint32_t dynamiteAmmunition;
    uint8_t unknown_before_0xe8[0x6c];
    uint32_t attackSequence;
    uint8_t unknown_before_0x100[0x14];
    uint32_t unknown_0x100;
    uint32_t unknown_0x104;
    uint32_t unknown_0x108;
    uint8_t unknown_before_0x120[0x14];
    uint32_t unknown_0x120;
    uint32_t savedAnimation;
    uint32_t nextAnimation;
    uint32_t heldActor;
};
static_assert(std::is_standard_layout<AttackPrivatePrefixLayout>::value, "v1.3 attack layout");
static_assert(sizeof(AttackPrivatePrefixLayout) == 0x130 && alignof(AttackPrivatePrefixLayout) == 4, "v1.3 observed attack prefix");
static_assert(offsetof(AttackPrivatePrefixLayout, facing) == 0x0, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, active) == 0x4, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, unknown_0x10) == 0x10, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, unknown_0x14) == 0x14, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, animationPending) == 0x1c, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, cancelled) == 0x20, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, attackId) == 0x3c, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, unknown_0x54) == 0x54, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, unknown_0x58) == 0x58, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, weaponMode) == 0x6c, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, pistolAmmunition) == 0x70, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, magicAmmunition) == 0x74, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, dynamiteAmmunition) == 0x78, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, attackSequence) == 0xe8, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, unknown_0x100) == 0x100, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, unknown_0x104) == 0x104, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, unknown_0x108) == 0x108, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, unknown_0x120) == 0x120, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, savedAnimation) == 0x124, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, nextAnimation) == 0x128, "v1.3 0x41f270 original field");
static_assert(offsetof(AttackPrivatePrefixLayout, heldActor) == 0x12c, "v1.3 0x41f270 original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class AttackActorFields {
  public:
    AttackActorFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(AttackActorPrefixLayout, flags))
    CLAW_RECOVERED_FIELD(scene, offsetof(AttackActorPrefixLayout, scene))
    CLAW_RECOVERED_FIELD(logicHolder, offsetof(AttackActorPrefixLayout, logicHolder))
    CLAW_RECOVERED_FIELD(damage, offsetof(AttackActorPrefixLayout, damage))
    CLAW_RECOVERED_FIELD(attackLeft, offsetof(AttackActorPrefixLayout, attackLeft))
    CLAW_RECOVERED_FIELD(attackTop, offsetof(AttackActorPrefixLayout, attackTop))
    CLAW_RECOVERED_FIELD(attackRight, offsetof(AttackActorPrefixLayout, attackRight))
    CLAW_RECOVERED_FIELD(attackBottom, offsetof(AttackActorPrefixLayout, attackBottom))
    CLAW_RECOVERED_FIELD(savedAnimationSource, offsetof(AttackActorPrefixLayout, savedAnimationSource))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class AttackPrivateFields {
  public:
    AttackPrivateFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(facing, offsetof(AttackPrivatePrefixLayout, facing))
    CLAW_RECOVERED_FIELD(active, offsetof(AttackPrivatePrefixLayout, active))
    CLAW_RECOVERED_FIELD(unknown_0x10, offsetof(AttackPrivatePrefixLayout, unknown_0x10))
    CLAW_RECOVERED_FIELD(unknown_0x14, offsetof(AttackPrivatePrefixLayout, unknown_0x14))
    CLAW_RECOVERED_FIELD(animationPending, offsetof(AttackPrivatePrefixLayout, animationPending))
    CLAW_RECOVERED_FIELD(cancelled, offsetof(AttackPrivatePrefixLayout, cancelled))
    CLAW_RECOVERED_FIELD(attackId, offsetof(AttackPrivatePrefixLayout, attackId))
    CLAW_RECOVERED_FIELD(unknown_0x54, offsetof(AttackPrivatePrefixLayout, unknown_0x54))
    CLAW_RECOVERED_FIELD(unknown_0x58, offsetof(AttackPrivatePrefixLayout, unknown_0x58))
    CLAW_RECOVERED_FIELD(weaponMode, offsetof(AttackPrivatePrefixLayout, weaponMode))
    CLAW_RECOVERED_FIELD(pistolAmmunition, offsetof(AttackPrivatePrefixLayout, pistolAmmunition))
    CLAW_RECOVERED_FIELD(magicAmmunition, offsetof(AttackPrivatePrefixLayout, magicAmmunition))
    CLAW_RECOVERED_FIELD(dynamiteAmmunition, offsetof(AttackPrivatePrefixLayout, dynamiteAmmunition))
    CLAW_RECOVERED_FIELD(attackSequence, offsetof(AttackPrivatePrefixLayout, attackSequence))
    CLAW_RECOVERED_FIELD(unknown_0x100, offsetof(AttackPrivatePrefixLayout, unknown_0x100))
    CLAW_RECOVERED_FIELD(unknown_0x104, offsetof(AttackPrivatePrefixLayout, unknown_0x104))
    CLAW_RECOVERED_FIELD(unknown_0x108, offsetof(AttackPrivatePrefixLayout, unknown_0x108))
    CLAW_RECOVERED_FIELD(unknown_0x120, offsetof(AttackPrivatePrefixLayout, unknown_0x120))
    CLAW_RECOVERED_FIELD(savedAnimation, offsetof(AttackPrivatePrefixLayout, savedAnimation))
    CLAW_RECOVERED_FIELD(nextAnimation, offsetof(AttackPrivatePrefixLayout, nextAnimation))
    CLAW_RECOVERED_FIELD(heldActor, offsetof(AttackPrivatePrefixLayout, heldActor))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

// v1.3 keyboard-input byte contracts. These are observed prefixes only;
// transport-bound views do not materialize or overlay guest storage.
struct CheatRecognizerPrefixLayout {
    uint32_t window;
    uint8_t dictionary[0x1c];
    uint8_t encodedText[0x100];
    uint32_t length;
    uint32_t lastInputMilliseconds;
    uint32_t cheated;
};
static_assert(std::is_standard_layout<CheatRecognizerPrefixLayout>::value, "layout contract");
static_assert(sizeof(CheatRecognizerPrefixLayout) == 0x12c && alignof(CheatRecognizerPrefixLayout) == 4, "v1.3 input prefix");
static_assert(offsetof(CheatRecognizerPrefixLayout, window) == 0x0, "v13_cheat_input original field");
static_assert(offsetof(CheatRecognizerPrefixLayout, dictionary) == 0x4, "v13_cheat_input original field");
static_assert(offsetof(CheatRecognizerPrefixLayout, encodedText) == 0x20, "v13_cheat_input original field");
static_assert(offsetof(CheatRecognizerPrefixLayout, length) == 0x120, "v13_cheat_input original field");
static_assert(offsetof(CheatRecognizerPrefixLayout, lastInputMilliseconds) == 0x124, "v13_cheat_input original field");
static_assert(offsetof(CheatRecognizerPrefixLayout, cheated) == 0x128, "v13_cheat_input original field");

struct CheatCommandPrefixLayout {
    uint32_t command;
    uint8_t flags;
    uint8_t unknown_after_0x5[0x3];
};
static_assert(std::is_standard_layout<CheatCommandPrefixLayout>::value, "layout contract");
static_assert(sizeof(CheatCommandPrefixLayout) == 0x8 && alignof(CheatCommandPrefixLayout) == 4, "v1.3 input prefix");
static_assert(offsetof(CheatCommandPrefixLayout, command) == 0x0, "v13_cheat_input original field");
static_assert(offsetof(CheatCommandPrefixLayout, flags) == 0x4, "v13_cheat_input original field");

struct GameplayInputPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t application;
};
static_assert(std::is_standard_layout<GameplayInputPrefixLayout>::value, "layout contract");
static_assert(sizeof(GameplayInputPrefixLayout) == 0x8 && alignof(GameplayInputPrefixLayout) == 4, "v1.3 input prefix");
static_assert(offsetof(GameplayInputPrefixLayout, application) == 0x4, "v13_cheat_input original field");

struct InputApplicationPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t windowOwner;
    uint8_t unknown_before_0xc[0x4];
    uint32_t paused;
    uint8_t unknown_before_0x48[0x38];
    uint32_t cheatRecognizer;
};
static_assert(std::is_standard_layout<InputApplicationPrefixLayout>::value, "layout contract");
static_assert(sizeof(InputApplicationPrefixLayout) == 0x4c && alignof(InputApplicationPrefixLayout) == 4, "v1.3 input prefix");
static_assert(offsetof(InputApplicationPrefixLayout, windowOwner) == 0x4, "v13_cheat_input original field");
static_assert(offsetof(InputApplicationPrefixLayout, paused) == 0xc, "v13_cheat_input original field");
static_assert(offsetof(InputApplicationPrefixLayout, cheatRecognizer) == 0x48, "v13_cheat_input original field");

struct InputWindowPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t window;
};
static_assert(std::is_standard_layout<InputWindowPrefixLayout>::value, "layout contract");
static_assert(sizeof(InputWindowPrefixLayout) == 0x8 && alignof(InputWindowPrefixLayout) == 4, "v1.3 input prefix");
static_assert(offsetof(InputWindowPrefixLayout, window) == 0x4, "v13_cheat_input original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class CheatRecognizerFields {
  public:
    CheatRecognizerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(window, offsetof(CheatRecognizerPrefixLayout, window))
    CLAW_RECOVERED_FIELD(length, offsetof(CheatRecognizerPrefixLayout, length))
    CLAW_RECOVERED_FIELD(lastInputMilliseconds, offsetof(CheatRecognizerPrefixLayout, lastInputMilliseconds))
    CLAW_RECOVERED_FIELD(cheated, offsetof(CheatRecognizerPrefixLayout, cheated))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class CheatCommandFields {
  public:
    CheatCommandFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(command, offsetof(CheatCommandPrefixLayout, command))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class GameplayInputFields {
  public:
    GameplayInputFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(application, offsetof(GameplayInputPrefixLayout, application))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class InputApplicationFields {
  public:
    InputApplicationFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(windowOwner, offsetof(InputApplicationPrefixLayout, windowOwner))
    CLAW_RECOVERED_FIELD(paused, offsetof(InputApplicationPrefixLayout, paused))
    CLAW_RECOVERED_FIELD(cheatRecognizer, offsetof(InputApplicationPrefixLayout, cheatRecognizer))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class InputWindowFields {
  public:
    InputWindowFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(window, offsetof(InputWindowPrefixLayout, window))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get8(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put8(token_ + uint32_t(Offset) + uint32_t(Delta), uint8_t(value)); \
    }

template<class Memory> class CheatCommandByteFields {
  public:
    CheatCommandByteFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(flags, offsetof(CheatCommandPrefixLayout, flags))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class CheatTextByteFields {
  public:
    CheatTextByteFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(encodedText, offsetof(CheatRecognizerPrefixLayout, encodedText))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD


// Version 1.3 command-dispatch observed prefixes (0x42a9b0 and text helpers).
// Descriptors only: fields use guest transport, never C++ overlays.
struct DispatchApplicationPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t windowOwner;
    uint8_t unknown_before_0x14[0xc];
    uint32_t musicEnabled;
    uint8_t unknown_before_0x2c[0x14];
    uint32_t state;
    uint32_t resources;
    uint8_t unknown_before_0x4c[0x18];
    uint32_t acknowledgements;
    uint32_t musicManager;
    uint8_t unknown_before_0x78[0x24];
    uint32_t displayDepth;
    uint32_t displayWidth;
};
static_assert(std::is_standard_layout<DispatchApplicationPrefixLayout>::value, "v1.3 dispatch layout");
static_assert(sizeof(DispatchApplicationPrefixLayout) == 0x80 && alignof(DispatchApplicationPrefixLayout) == 4, "v1.3 observed dispatch prefix");
static_assert(offsetof(DispatchApplicationPrefixLayout, windowOwner) == 0x4, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchApplicationPrefixLayout, musicEnabled) == 0x14, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchApplicationPrefixLayout, state) == 0x2c, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchApplicationPrefixLayout, resources) == 0x30, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchApplicationPrefixLayout, acknowledgements) == 0x4c, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchApplicationPrefixLayout, musicManager) == 0x50, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchApplicationPrefixLayout, displayDepth) == 0x78, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchApplicationPrefixLayout, displayWidth) == 0x7c, "v13_cheat_dispatch original field");

struct DispatchResourceOwnerPrefixLayout {
    uint8_t unknown_before_0x28[0x28];
    uint32_t soundManager;
};
static_assert(std::is_standard_layout<DispatchResourceOwnerPrefixLayout>::value, "v1.3 dispatch layout");
static_assert(sizeof(DispatchResourceOwnerPrefixLayout) == 0x2c && alignof(DispatchResourceOwnerPrefixLayout) == 4, "v1.3 observed dispatch prefix");
static_assert(offsetof(DispatchResourceOwnerPrefixLayout, soundManager) == 0x28, "v13_cheat_dispatch original field");

struct DispatchSoundManagerPrefixLayout {
    uint8_t unknown_before_0x30[0x30];
    uint32_t namedLookupDisabled;
};
static_assert(std::is_standard_layout<DispatchSoundManagerPrefixLayout>::value, "v1.3 dispatch layout");
static_assert(sizeof(DispatchSoundManagerPrefixLayout) == 0x34 && alignof(DispatchSoundManagerPrefixLayout) == 4, "v1.3 observed dispatch prefix");
static_assert(offsetof(DispatchSoundManagerPrefixLayout, namedLookupDisabled) == 0x30, "v13_cheat_dispatch original field");

struct DispatchSoundPrefixLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t backend;
    uint32_t lastRequestMilliseconds;
    uint32_t requestIntervalMilliseconds;
};
static_assert(std::is_standard_layout<DispatchSoundPrefixLayout>::value, "v1.3 dispatch layout");
static_assert(sizeof(DispatchSoundPrefixLayout) == 0x1c && alignof(DispatchSoundPrefixLayout) == 4, "v1.3 observed dispatch prefix");
static_assert(offsetof(DispatchSoundPrefixLayout, backend) == 0x10, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchSoundPrefixLayout, lastRequestMilliseconds) == 0x14, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchSoundPrefixLayout, requestIntervalMilliseconds) == 0x18, "v13_cheat_dispatch original field");

struct DispatchTextListPrefixLayout {
    uint8_t unknown_before_0xc[0xc];
    uint32_t entryCount;
};
static_assert(std::is_standard_layout<DispatchTextListPrefixLayout>::value, "v1.3 dispatch layout");
static_assert(sizeof(DispatchTextListPrefixLayout) == 0x10 && alignof(DispatchTextListPrefixLayout) == 4, "v1.3 observed dispatch prefix");
static_assert(offsetof(DispatchTextListPrefixLayout, entryCount) == 0xc, "v13_cheat_dispatch original field");

struct DispatchMusicManagerPrefixLayout {
    uint8_t unknown_before_0x1c[0x1c];
    uint32_t sequence;
};
static_assert(std::is_standard_layout<DispatchMusicManagerPrefixLayout>::value, "v1.3 dispatch layout");
static_assert(sizeof(DispatchMusicManagerPrefixLayout) == 0x20 && alignof(DispatchMusicManagerPrefixLayout) == 4, "v1.3 observed dispatch prefix");
static_assert(offsetof(DispatchMusicManagerPrefixLayout, sequence) == 0x1c, "v13_cheat_dispatch original field");

struct DispatchCommandRecordPrefixLayout {
    uint8_t unknown_before_0xb4[0xb4];
    uint32_t unknown_0xb4;
    uint32_t unknown_0xb8;
};
static_assert(std::is_standard_layout<DispatchCommandRecordPrefixLayout>::value, "v1.3 dispatch layout");
static_assert(sizeof(DispatchCommandRecordPrefixLayout) == 0xbc && alignof(DispatchCommandRecordPrefixLayout) == 4, "v1.3 observed dispatch prefix");
static_assert(offsetof(DispatchCommandRecordPrefixLayout, unknown_0xb4) == 0xb4, "v13_cheat_dispatch original field");
static_assert(offsetof(DispatchCommandRecordPrefixLayout, unknown_0xb8) == 0xb8, "v13_cheat_dispatch original field");

struct DispatchStatePrefixLayout {
    uint8_t unknown_before_0x2c[0x2c];
    uint32_t paletteOwner;
};
static_assert(std::is_standard_layout<DispatchStatePrefixLayout>::value, "v1.3 dispatch layout");
static_assert(sizeof(DispatchStatePrefixLayout) == 0x30 && alignof(DispatchStatePrefixLayout) == 4, "v1.3 observed dispatch prefix");
static_assert(offsetof(DispatchStatePrefixLayout, paletteOwner) == 0x2c, "v13_cheat_dispatch original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class DispatchApplicationFields {
  public:
    DispatchApplicationFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(windowOwner, offsetof(DispatchApplicationPrefixLayout, windowOwner))
    CLAW_RECOVERED_FIELD(musicEnabled, offsetof(DispatchApplicationPrefixLayout, musicEnabled))
    CLAW_RECOVERED_FIELD(state, offsetof(DispatchApplicationPrefixLayout, state))
    CLAW_RECOVERED_FIELD(resources, offsetof(DispatchApplicationPrefixLayout, resources))
    CLAW_RECOVERED_FIELD(acknowledgements, offsetof(DispatchApplicationPrefixLayout, acknowledgements))
    CLAW_RECOVERED_FIELD(musicManager, offsetof(DispatchApplicationPrefixLayout, musicManager))
    CLAW_RECOVERED_FIELD(displayDepth, offsetof(DispatchApplicationPrefixLayout, displayDepth))
    CLAW_RECOVERED_FIELD(displayWidth, offsetof(DispatchApplicationPrefixLayout, displayWidth))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class DispatchResourceOwnerFields {
  public:
    DispatchResourceOwnerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(soundManager, offsetof(DispatchResourceOwnerPrefixLayout, soundManager))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class DispatchSoundManagerFields {
  public:
    DispatchSoundManagerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(namedLookupDisabled, offsetof(DispatchSoundManagerPrefixLayout, namedLookupDisabled))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class DispatchSoundFields {
  public:
    DispatchSoundFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(backend, offsetof(DispatchSoundPrefixLayout, backend))
    CLAW_RECOVERED_FIELD(lastRequestMilliseconds, offsetof(DispatchSoundPrefixLayout, lastRequestMilliseconds))
    CLAW_RECOVERED_FIELD(requestIntervalMilliseconds, offsetof(DispatchSoundPrefixLayout, requestIntervalMilliseconds))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class DispatchTextListFields {
  public:
    DispatchTextListFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(entryCount, offsetof(DispatchTextListPrefixLayout, entryCount))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class DispatchMusicManagerFields {
  public:
    DispatchMusicManagerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(sequence, offsetof(DispatchMusicManagerPrefixLayout, sequence))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class DispatchCommandRecordFields {
  public:
    DispatchCommandRecordFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0xb4, offsetof(DispatchCommandRecordPrefixLayout, unknown_0xb4))
    CLAW_RECOVERED_FIELD(unknown_0xb8, offsetof(DispatchCommandRecordPrefixLayout, unknown_0xb8))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class DispatchStateFields {
  public:
    DispatchStateFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(paletteOwner, offsetof(DispatchStatePrefixLayout, paletteOwner))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

// Version 1.3 contact records observed by v13_contact_bindings.
// Descriptions of guest bytes only; views never overlay guest storage.

struct ContactActorPrefixLayout {
    uint8_t unknown_before_0x4[0x4];
    uint32_t identity;
    uint8_t unknown_before_0xc[0x4];
    uint32_t scene;
    uint8_t unknown_before_0x7c[0x6c];
    uint32_t logicHolder;
    uint32_t hitLogic;
    uint8_t unknown_before_0x88[0x4];
    uint32_t attackLogic;
    uint8_t unknown_before_0x90[0x4];
    uint32_t bumpLogic;
};
static_assert(std::is_standard_layout<ContactActorPrefixLayout>::value, "v1.3 contact layout");
static_assert(sizeof(ContactActorPrefixLayout) == 0x94 && alignof(ContactActorPrefixLayout) == 4, "v1.3 observed contact record");
static_assert(offsetof(ContactActorPrefixLayout, identity) == 0x4, "v13_contact_bindings original field");
static_assert(offsetof(ContactActorPrefixLayout, scene) == 0xc, "v13_contact_bindings original field");
static_assert(offsetof(ContactActorPrefixLayout, logicHolder) == 0x7c, "v13_contact_bindings original field");
static_assert(offsetof(ContactActorPrefixLayout, hitLogic) == 0x80, "v13_contact_bindings original field");
static_assert(offsetof(ContactActorPrefixLayout, attackLogic) == 0x88, "v13_contact_bindings original field");
static_assert(offsetof(ContactActorPrefixLayout, bumpLogic) == 0x90, "v13_contact_bindings original field");

struct ContactScenePrefixLayout {
    uint8_t unknown_before_0x14[0x14];
    uint32_t registry;
};
static_assert(std::is_standard_layout<ContactScenePrefixLayout>::value, "v1.3 contact layout");
static_assert(sizeof(ContactScenePrefixLayout) == 0x18 && alignof(ContactScenePrefixLayout) == 4, "v1.3 observed contact record");
static_assert(offsetof(ContactScenePrefixLayout, registry) == 0x14, "v13_contact_bindings original field");

struct ContactMetadataPrefixLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t callback;
};
static_assert(std::is_standard_layout<ContactMetadataPrefixLayout>::value, "v1.3 contact layout");
static_assert(sizeof(ContactMetadataPrefixLayout) == 0x14 && alignof(ContactMetadataPrefixLayout) == 4, "v1.3 observed contact record");
static_assert(offsetof(ContactMetadataPrefixLayout, callback) == 0x10, "v13_contact_bindings original field");

struct ContactHolderPrefixLayout {
    uint8_t unknown_before_0x18[0x18];
    uint32_t child;
};
static_assert(std::is_standard_layout<ContactHolderPrefixLayout>::value, "v1.3 contact layout");
static_assert(sizeof(ContactHolderPrefixLayout) == 0x1c && alignof(ContactHolderPrefixLayout) == 4, "v1.3 observed contact record");
static_assert(offsetof(ContactHolderPrefixLayout, child) == 0x18, "v13_contact_bindings original field");

struct ContactLogicLayout {
    uint32_t vtable;
    uint32_t identity;
    uint32_t context;
    uint32_t scene;
    uint32_t callback;
    uint32_t data;
    uint32_t child;
    uint32_t unknown_0x1c;
    uint32_t unknown_0x20;
    uint32_t unknown_0x24;
    uint32_t unknown_0x28;
    uint32_t unknown_0x2c;
    uint32_t unknown_0x30;
    uint32_t unknown_0x34;
    uint32_t unknown_0x38;
    uint8_t unknown_before_0x168[0x12c];
    uint32_t unknown_0x168;
    uint32_t unknown_0x16c;
    uint32_t unknown_0x170;
    uint32_t unknown_0x174;
    uint32_t unknown_0x178;
};
static_assert(std::is_standard_layout<ContactLogicLayout>::value, "v1.3 contact layout");
static_assert(sizeof(ContactLogicLayout) == 0x17c && alignof(ContactLogicLayout) == 4, "v1.3 observed contact record");
static_assert(offsetof(ContactLogicLayout, vtable) == 0x0, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, identity) == 0x4, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, context) == 0x8, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, scene) == 0xc, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, callback) == 0x10, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, data) == 0x14, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, child) == 0x18, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x1c) == 0x1c, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x20) == 0x20, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x24) == 0x24, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x28) == 0x28, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x2c) == 0x2c, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x30) == 0x30, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x34) == 0x34, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x38) == 0x38, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x168) == 0x168, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x16c) == 0x16c, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x170) == 0x170, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x174) == 0x174, "v13_contact_bindings original field");
static_assert(offsetof(ContactLogicLayout, unknown_0x178) == 0x178, "v13_contact_bindings original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class ContactActorFields {
  public:
    ContactActorFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(identity, offsetof(ContactActorPrefixLayout, identity))
    CLAW_RECOVERED_FIELD(scene, offsetof(ContactActorPrefixLayout, scene))
    CLAW_RECOVERED_FIELD(logicHolder, offsetof(ContactActorPrefixLayout, logicHolder))
    CLAW_RECOVERED_FIELD(hitLogic, offsetof(ContactActorPrefixLayout, hitLogic))
    CLAW_RECOVERED_FIELD(attackLogic, offsetof(ContactActorPrefixLayout, attackLogic))
    CLAW_RECOVERED_FIELD(bumpLogic, offsetof(ContactActorPrefixLayout, bumpLogic))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ContactSceneFields {
  public:
    ContactSceneFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(registry, offsetof(ContactScenePrefixLayout, registry))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ContactMetadataFields {
  public:
    ContactMetadataFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(callback, offsetof(ContactMetadataPrefixLayout, callback))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ContactHolderFields {
  public:
    ContactHolderFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(child, offsetof(ContactHolderPrefixLayout, child))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class ContactLogicFields {
  public:
    ContactLogicFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(vtable, offsetof(ContactLogicLayout, vtable))
    CLAW_RECOVERED_FIELD(identity, offsetof(ContactLogicLayout, identity))
    CLAW_RECOVERED_FIELD(context, offsetof(ContactLogicLayout, context))
    CLAW_RECOVERED_FIELD(scene, offsetof(ContactLogicLayout, scene))
    CLAW_RECOVERED_FIELD(callback, offsetof(ContactLogicLayout, callback))
    CLAW_RECOVERED_FIELD(data, offsetof(ContactLogicLayout, data))
    CLAW_RECOVERED_FIELD(child, offsetof(ContactLogicLayout, child))
    CLAW_RECOVERED_FIELD(unknown_0x1c, offsetof(ContactLogicLayout, unknown_0x1c))
    CLAW_RECOVERED_FIELD(unknown_0x20, offsetof(ContactLogicLayout, unknown_0x20))
    CLAW_RECOVERED_FIELD(unknown_0x24, offsetof(ContactLogicLayout, unknown_0x24))
    CLAW_RECOVERED_FIELD(unknown_0x28, offsetof(ContactLogicLayout, unknown_0x28))
    CLAW_RECOVERED_FIELD(unknown_0x2c, offsetof(ContactLogicLayout, unknown_0x2c))
    CLAW_RECOVERED_FIELD(unknown_0x30, offsetof(ContactLogicLayout, unknown_0x30))
    CLAW_RECOVERED_FIELD(unknown_0x34, offsetof(ContactLogicLayout, unknown_0x34))
    CLAW_RECOVERED_FIELD(unknown_0x38, offsetof(ContactLogicLayout, unknown_0x38))
    CLAW_RECOVERED_FIELD(unknown_0x168, offsetof(ContactLogicLayout, unknown_0x168))
    CLAW_RECOVERED_FIELD(unknown_0x16c, offsetof(ContactLogicLayout, unknown_0x16c))
    CLAW_RECOVERED_FIELD(unknown_0x170, offsetof(ContactLogicLayout, unknown_0x170))
    CLAW_RECOVERED_FIELD(unknown_0x174, offsetof(ContactLogicLayout, unknown_0x174))
    CLAW_RECOVERED_FIELD(unknown_0x178, offsetof(ContactLogicLayout, unknown_0x178))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD


// v1.3 serialization lifecycle prefixes (0x4c7930 / 0x4d6590).
// Byte contracts only: no native object is overlaid on guest storage.
struct LifecycleActorPrefixLayout {
    uint8_t unknown_before_0xc[0xc];
    uint32_t scene;
    uint8_t unknown_before_0x7c[0x6c];
    uint32_t logicHolder;
    uint8_t unknown_before_0x98[0x18];
    uint32_t peer;
    uint8_t unknown_before_0x184[0xe8];
    uint32_t serializedPeerIdentity;
    uint32_t numericIdentity;
};
static_assert(std::is_standard_layout<LifecycleActorPrefixLayout>::value, "v1.3 lifecycle layout");
static_assert(sizeof(LifecycleActorPrefixLayout) == 0x18c && alignof(LifecycleActorPrefixLayout) == 4, "v1.3 observed lifecycle prefix");
static_assert(offsetof(LifecycleActorPrefixLayout, scene) == 0xc, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleActorPrefixLayout, logicHolder) == 0x7c, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleActorPrefixLayout, peer) == 0x98, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleActorPrefixLayout, serializedPeerIdentity) == 0x184, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleActorPrefixLayout, numericIdentity) == 0x188, "v13_raw_lifecycle original field");

struct LifecycleLogicPrefixLayout {
    uint8_t unknown_before_0xc[0xc];
    uint32_t scene;
    uint32_t callback;
    uint8_t unknown_before_0x18[0x4];
    uint32_t child;
    uint32_t event;
    uint8_t unknown_before_0x170[0x150];
    uint32_t peer;
    uint32_t serializedPeerIdentity;
};
static_assert(std::is_standard_layout<LifecycleLogicPrefixLayout>::value, "v1.3 lifecycle layout");
static_assert(sizeof(LifecycleLogicPrefixLayout) == 0x178 && alignof(LifecycleLogicPrefixLayout) == 4, "v1.3 observed lifecycle prefix");
static_assert(offsetof(LifecycleLogicPrefixLayout, scene) == 0xc, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleLogicPrefixLayout, callback) == 0x10, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleLogicPrefixLayout, child) == 0x18, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleLogicPrefixLayout, event) == 0x1c, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleLogicPrefixLayout, peer) == 0x170, "v13_raw_lifecycle original field");
static_assert(offsetof(LifecycleLogicPrefixLayout, serializedPeerIdentity) == 0x174, "v13_raw_lifecycle original field");

struct LifecycleScenePrefixLayout {
    uint8_t unknown_before_0x8[0x8];
    uint32_t objects;
};
static_assert(std::is_standard_layout<LifecycleScenePrefixLayout>::value, "v1.3 lifecycle layout");
static_assert(sizeof(LifecycleScenePrefixLayout) == 0xc && alignof(LifecycleScenePrefixLayout) == 4, "v1.3 observed lifecycle prefix");
static_assert(offsetof(LifecycleScenePrefixLayout, objects) == 0x8, "v13_raw_lifecycle original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class LifecycleActorFields {
  public:
    LifecycleActorFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(scene, offsetof(LifecycleActorPrefixLayout, scene))
    CLAW_RECOVERED_FIELD(logicHolder, offsetof(LifecycleActorPrefixLayout, logicHolder))
    CLAW_RECOVERED_FIELD(peer, offsetof(LifecycleActorPrefixLayout, peer))
    CLAW_RECOVERED_FIELD(serializedPeerIdentity, offsetof(LifecycleActorPrefixLayout, serializedPeerIdentity))
    CLAW_RECOVERED_FIELD(numericIdentity, offsetof(LifecycleActorPrefixLayout, numericIdentity))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class LifecycleLogicFields {
  public:
    LifecycleLogicFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(scene, offsetof(LifecycleLogicPrefixLayout, scene))
    CLAW_RECOVERED_FIELD(callback, offsetof(LifecycleLogicPrefixLayout, callback))
    CLAW_RECOVERED_FIELD(child, offsetof(LifecycleLogicPrefixLayout, child))
    CLAW_RECOVERED_FIELD(event, offsetof(LifecycleLogicPrefixLayout, event))
    CLAW_RECOVERED_FIELD(peer, offsetof(LifecycleLogicPrefixLayout, peer))
    CLAW_RECOVERED_FIELD(serializedPeerIdentity, offsetof(LifecycleLogicPrefixLayout, serializedPeerIdentity))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class LifecycleSceneFields {
  public:
    LifecycleSceneFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(objects, offsetof(LifecycleScenePrefixLayout, objects))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD


// Raw serialization byte contracts only; never overlays on guest memory.
// Unknown regions retain the offset and width established by stream calls.
struct RawActorStreamLayout {
    uint32_t unknown_0x0;
    uint32_t unknown_0x4;
    uint32_t unknown_0x8;
    uint32_t scene;
    uint32_t unknown_0x10;
    uint32_t unknown_0x14;
    uint32_t unknown_0x18[0x9];
    uint8_t unknown_before_0x40[0x4];
    uint32_t unknown_0x40;
    uint32_t unknown_0x44;
    uint32_t unknown_0x48;
    uint8_t unknown_before_0x50[0x4];
    uint32_t unknown_0x50;
    uint32_t unknown_0x54;
    uint32_t unknown_0x58;
    uint8_t unknown_before_0x64[0x8];
    uint32_t unknown_0x64[0x4];
    uint8_t unknown_before_0x80[0xc];
    uint32_t binding0;
    uint8_t unknown_before_0x88[0x4];
    uint32_t binding1;
    uint8_t unknown_before_0x90[0x4];
    uint32_t binding2;
    uint8_t unknown_before_0xb8[0x24];
    uint32_t fixedHeader[0x9];
    uint32_t name;
    uint8_t unknown_before_0xe4[0x4];
    uint32_t unknown_0xe4[0x14];
    uint32_t unknown_0x134[0xc];
    uint32_t unknown_0x164[0x8];
    uint32_t serializedPeerIdentity;
};
static_assert(std::is_standard_layout<RawActorStreamLayout>::value, "v1.3 raw serialization layout");
static_assert(sizeof(RawActorStreamLayout) == 0x188 && alignof(RawActorStreamLayout) == 4, "v1.3 raw serialization extent");
static_assert(offsetof(RawActorStreamLayout, unknown_0x0) == 0x0, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x4) == 0x4, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x8) == 0x8, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, scene) == 0xc, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x10) == 0x10, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x14) == 0x14, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x18) == 0x18, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x40) == 0x40, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x44) == 0x44, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x48) == 0x48, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x50) == 0x50, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x54) == 0x54, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x58) == 0x58, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x64) == 0x64, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, binding0) == 0x80, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, binding1) == 0x88, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, binding2) == 0x90, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, fixedHeader) == 0xb8, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, name) == 0xdc, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0xe4) == 0xe4, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x134) == 0x134, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, unknown_0x164) == 0x164, "v13_raw_fields original region");
static_assert(offsetof(RawActorStreamLayout, serializedPeerIdentity) == 0x184, "v13_raw_fields original region");

struct RawLogicStreamLayout {
    uint8_t unknown_before_0x14[0x14];
    uint32_t payload;
    uint8_t unknown_before_0x1c[0x4];
    uint32_t unknown_0x1c[0x2d];
    uint32_t unknown_0xd0[0x18];
    uint32_t unknown_0x130[0xe];
    uint8_t unknown_before_0x174[0xc];
    uint32_t serializedPeerIdentity;
    uint32_t payloadByteCount;
};
static_assert(std::is_standard_layout<RawLogicStreamLayout>::value, "v1.3 raw serialization layout");
static_assert(sizeof(RawLogicStreamLayout) == 0x17c && alignof(RawLogicStreamLayout) == 4, "v1.3 raw serialization extent");
static_assert(offsetof(RawLogicStreamLayout, payload) == 0x14, "v13_raw_fields original region");
static_assert(offsetof(RawLogicStreamLayout, unknown_0x1c) == 0x1c, "v13_raw_fields original region");
static_assert(offsetof(RawLogicStreamLayout, unknown_0xd0) == 0xd0, "v13_raw_fields original region");
static_assert(offsetof(RawLogicStreamLayout, unknown_0x130) == 0x130, "v13_raw_fields original region");
static_assert(offsetof(RawLogicStreamLayout, serializedPeerIdentity) == 0x174, "v13_raw_fields original region");
static_assert(offsetof(RawLogicStreamLayout, payloadByteCount) == 0x178, "v13_raw_fields original region");

struct RawNameRegistryPrefixLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t nameMapPrefix[0x3];
    uint32_t entryCount;
};
static_assert(std::is_standard_layout<RawNameRegistryPrefixLayout>::value, "v1.3 raw serialization layout");
static_assert(sizeof(RawNameRegistryPrefixLayout) == 0x20 && alignof(RawNameRegistryPrefixLayout) == 4, "v1.3 raw serialization extent");
static_assert(offsetof(RawNameRegistryPrefixLayout, nameMapPrefix) == 0x10, "v13_raw_fields original region");
static_assert(offsetof(RawNameRegistryPrefixLayout, entryCount) == 0x1c, "v13_raw_fields original region");

struct RawRegistryValuePrefixLayout {
    uint8_t unknown_before_0x10[0x10];
    uint32_t lookupIdentity;
};
static_assert(std::is_standard_layout<RawRegistryValuePrefixLayout>::value, "v1.3 raw serialization layout");
static_assert(sizeof(RawRegistryValuePrefixLayout) == 0x14 && alignof(RawRegistryValuePrefixLayout) == 4, "v1.3 raw serialization extent");
static_assert(offsetof(RawRegistryValuePrefixLayout, lookupIdentity) == 0x10, "v13_raw_fields original region");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class RawActorStreamFields {
  public:
    RawActorStreamFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(scene, offsetof(RawActorStreamLayout, scene))
    CLAW_RECOVERED_FIELD(name, offsetof(RawActorStreamLayout, name))
    CLAW_RECOVERED_FIELD(binding0, offsetof(RawActorStreamLayout, binding0))
    CLAW_RECOVERED_FIELD(binding1, offsetof(RawActorStreamLayout, binding1))
    CLAW_RECOVERED_FIELD(binding2, offsetof(RawActorStreamLayout, binding2))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class RawLogicStreamFields {
  public:
    RawLogicStreamFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(payload, offsetof(RawLogicStreamLayout, payload))
    CLAW_RECOVERED_FIELD(payloadByteCount, offsetof(RawLogicStreamLayout, payloadByteCount))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class RawNameRegistryFields {
  public:
    RawNameRegistryFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(entryCount, offsetof(RawNameRegistryPrefixLayout, entryCount))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class RawRegistryValueFields {
  public:
    RawRegistryValueFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(lookupIdentity, offsetof(RawRegistryValuePrefixLayout, lookupIdentity))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD


// v1.3 child serializers: byte contracts only, never guest-memory overlays.
// Numeric operands remain raw words, without host floating conversion.
struct RawChildBaseLayout {
    uint32_t unknown_0x0;
    uint32_t unknown_0x4;
    uint32_t unknown_0x8;
    uint32_t owner;
    uint32_t ownerAlias;
    uint32_t ownerWord;
    uint32_t bitset[0x4];
    uint32_t unknown_0x28;
    uint32_t unknown_0x2c;
    uint32_t unknown_0x30;
};
static_assert(std::is_standard_layout<RawChildBaseLayout>::value, "v1.3 child layout");
static_assert(sizeof(RawChildBaseLayout) == 0x34 && alignof(RawChildBaseLayout) == 4, "v1.3 child byte extent");
static_assert(offsetof(RawChildBaseLayout, unknown_0x0) == 0x0, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, unknown_0x4) == 0x4, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, unknown_0x8) == 0x8, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, owner) == 0xc, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, ownerAlias) == 0x10, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, ownerWord) == 0x14, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, bitset) == 0x18, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, unknown_0x28) == 0x28, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, unknown_0x2c) == 0x2c, "v13_raw_children original field");
static_assert(offsetof(RawChildBaseLayout, unknown_0x30) == 0x30, "v13_raw_children original field");
struct RawChildNumericLayout {
    uint32_t unknown_0x0[0x16];
    uint32_t skipped_0x58[0x6];
    uint32_t unknown_0x70[0x12];
    uint32_t signedIntegerBits;
    uint32_t skipped_0xbc;
    uint32_t unknown_0xc0[0x12];
};
static_assert(std::is_standard_layout<RawChildNumericLayout>::value, "v1.3 child layout");
static_assert(sizeof(RawChildNumericLayout) == 0x108 && alignof(RawChildNumericLayout) == 4, "v1.3 child byte extent");
static_assert(offsetof(RawChildNumericLayout, unknown_0x0) == 0x0, "v13_raw_children original field");
static_assert(offsetof(RawChildNumericLayout, skipped_0x58) == 0x58, "v13_raw_children original field");
static_assert(offsetof(RawChildNumericLayout, unknown_0x70) == 0x70, "v13_raw_children original field");
static_assert(offsetof(RawChildNumericLayout, signedIntegerBits) == 0xb8, "v13_raw_children original field");
static_assert(offsetof(RawChildNumericLayout, skipped_0xbc) == 0xbc, "v13_raw_children original field");
static_assert(offsetof(RawChildNumericLayout, unknown_0xc0) == 0xc0, "v13_raw_children original field");
struct RawChildOwnerPrefixLayout {
    uint32_t unknown_before_0x7c[0x1f];
    uint32_t unknown_0x7c;
};
static_assert(std::is_standard_layout<RawChildOwnerPrefixLayout>::value, "v1.3 child layout");
static_assert(sizeof(RawChildOwnerPrefixLayout) == 0x80 && alignof(RawChildOwnerPrefixLayout) == 4, "v1.3 child byte extent");
static_assert(offsetof(RawChildOwnerPrefixLayout, unknown_before_0x7c) == 0x0, "v13_raw_children original field");
static_assert(offsetof(RawChildOwnerPrefixLayout, unknown_0x7c) == 0x7c, "v13_raw_children original field");
struct RawChildDoubleWordsLayout {
    uint32_t low;
    uint32_t high;
};
static_assert(std::is_standard_layout<RawChildDoubleWordsLayout>::value, "v1.3 child layout");
static_assert(sizeof(RawChildDoubleWordsLayout) == 0x8 && alignof(RawChildDoubleWordsLayout) == 4, "v1.3 child byte extent");
static_assert(offsetof(RawChildDoubleWordsLayout, low) == 0x0, "v13_raw_children original field");
static_assert(offsetof(RawChildDoubleWordsLayout, high) == 0x4, "v13_raw_children original field");

struct RawChildDerivedLayout {
    uint8_t unknown_before_0x38[0x38];
    RawChildNumericLayout numeric;
    uint32_t unknown_0x140;
    uint32_t unknown_0x144;
    uint32_t unknown_0x148;
    uint32_t unknown_0x14c;
};
static_assert(std::is_standard_layout<RawChildDerivedLayout>::value, "v1.3 child layout");
static_assert(sizeof(RawChildDerivedLayout) == 0x150 && alignof(RawChildDerivedLayout) == 4, "v1.3 child byte extent");
static_assert(offsetof(RawChildDerivedLayout, numeric) == 0x38, "v13_raw_children original field");
static_assert(offsetof(RawChildDerivedLayout, unknown_0x140) == 0x140, "v13_raw_children original field");
static_assert(offsetof(RawChildDerivedLayout, unknown_0x144) == 0x144, "v13_raw_children original field");
static_assert(offsetof(RawChildDerivedLayout, unknown_0x148) == 0x148, "v13_raw_children original field");
static_assert(offsetof(RawChildDerivedLayout, unknown_0x14c) == 0x14c, "v13_raw_children original field");

#define CLAW_RECOVERED_FIELD(Name, Offset) \
    template<int32_t Delta = 0> uint32_t Name() const { \
        return memory_.get(token_ + uint32_t(Offset) + uint32_t(Delta)); \
    } \
    template<int32_t Delta = 0> void Name(uint32_t value) const { \
        memory_.put(token_ + uint32_t(Offset) + uint32_t(Delta), value); \
    }

template<class Memory> class RawChildBaseFields {
  public:
    RawChildBaseFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x4, offsetof(RawChildBaseLayout, unknown_0x4))
    CLAW_RECOVERED_FIELD(unknown_0x8, offsetof(RawChildBaseLayout, unknown_0x8))
    CLAW_RECOVERED_FIELD(owner, offsetof(RawChildBaseLayout, owner))
    CLAW_RECOVERED_FIELD(ownerAlias, offsetof(RawChildBaseLayout, ownerAlias))
    CLAW_RECOVERED_FIELD(ownerWord, offsetof(RawChildBaseLayout, ownerWord))
    CLAW_RECOVERED_FIELD(unknown_0x28, offsetof(RawChildBaseLayout, unknown_0x28))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class RawChildNumericFields {
  public:
    RawChildNumericFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(signedIntegerBits, offsetof(RawChildNumericLayout, signedIntegerBits))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class RawChildOwnerFields {
  public:
    RawChildOwnerFields(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(unknown_0x7c, offsetof(RawChildOwnerPrefixLayout, unknown_0x7c))
  private:
    Memory &memory_;
    uint32_t token_;
};

template<class Memory> class RawChildDoubleWords {
  public:
    RawChildDoubleWords(Memory &memory, uint32_t token) : memory_(memory), token_(token) {}
    CLAW_RECOVERED_FIELD(low, offsetof(RawChildDoubleWordsLayout, low))
    CLAW_RECOVERED_FIELD(high, offsetof(RawChildDoubleWordsLayout, high))
  private:
    Memory &memory_;
    uint32_t token_;
};

#undef CLAW_RECOVERED_FIELD

} // namespace v13
} // namespace recovered
} // namespace claw

#endif
