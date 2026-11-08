#ifndef CLAW_RECOVERED_NAMES_H
#define CLAW_RECOVERED_NAMES_H

#include <cstdint>

namespace claw {
namespace recovered {
namespace v10 {

// Tokens identify storage in the original 32-bit address space. These aliases
// intentionally do not acquire native pointer representation or ownership.
using ActorToken = uint32_t;
using LogicHolderToken = uint32_t;
using LogicToken = uint32_t;

// Names describe only the dispatch observed at original entry 0x40e690.
// The two virtual slots do not establish broader lifecycle semantics.
enum class BounceLogicState : uint32_t {
    Uninitialized = 0,
    CallVirtual20 = 0x1d,
    CallVirtual1c = 0x1e,
    Initialized = 0x3e8,
};


// Player/checkpoint/save chain: references remain original 32-bit tokens.
using SaveManagerToken = uint32_t;
using ProfileRecordToken = uint32_t;
using ProfileListNodeToken = uint32_t;
using ApplicationPlayerToken = uint32_t;
using PlayerListManagerToken = uint32_t;
using PlayerCacheToken = uint32_t;

// Death-message mode, byte limits and service slots observed in this family.
constexpr uint32_t DeathMessageMode = 0x4;
constexpr uint32_t DeathModeQuerySlot = 0x10;
constexpr uint32_t PlayerMessageTextLimitBytes = 0x80;
constexpr uint32_t MessagePlayerBufferBytes = 0x400;
constexpr uint32_t PlayerTextMessageKind = 0x3f0;
constexpr uint32_t PlayerMessageSendSlot = 0x68;

// Powerup IDs without established meanings retain their original numbers.
enum class PowerupKind : uint32_t {
    None = 0,
    Unknown0x26b7 = 0x26b7,
    Unknown0x26b8 = 0x26b8,
    Unknown0x26b9 = 0x26b9,
    Unknown0x26ba = 0x26ba,
    GlitterMother = 0x26bc,
    Unknown0x26bd = 0x26bd,
};
constexpr uint32_t PowerupGlobalsAddress = 0x534ea8;
constexpr uint32_t PowerupApplicationAddress = 0x5371fc;
constexpr uint32_t PowerupMusicSuppressionAddress = 0x53c9c0;
constexpr uint32_t MaximumPowerupAmount = 0xf3e58;
constexpr uint32_t FlareFrameInterval = 0x64;
constexpr uint32_t PowerupRemovalMask = 0x10000;
constexpr uint32_t PlayerPowerupRestoreMask = 0x1000044;
constexpr uint32_t PowerupMusicNameAddress = 0x524d78;
constexpr uint32_t LevelMusicNameAddress = 0x524d80;
constexpr uint32_t GlitterMotherNameAddress = 0x5225a0;

// End player/checkpoint/save chain.

// Actor storage/collision chain: sizes and flag tests observed at 0x4c8a20.
constexpr uint32_t PlainActorAllocationBytes = 0x168;
constexpr uint32_t ActorLogicHolderAllocationBytes = 0x174;
constexpr uint32_t ActorLogicHolderVtable = 0x513740;
constexpr uint32_t PlainActorBaseVtable = 0x513770;
constexpr uint32_t PlainActorVtable = 0x5137b0;
constexpr uint32_t SkipDepthInsertionFlag = 0x20000;
constexpr uint32_t CallPrimaryInitializerFlag = 0x200000;
// Tile cell sentinels and constant-return helpers observed in this family.
constexpr uint32_t EmptyTilePattern = 0xeeeeeeee;
constexpr uint32_t AbsentTilePattern = 0xffffffff;
constexpr uint32_t TileConstant14 = 0x14;
constexpr uint32_t TileConstant28 = 0x28;
// End actor storage/collision chain.

} // namespace v10

namespace v13 {

// Version 1.3 has its own layout and address contract; these remain guest tokens.
using ApplicationToken = uint32_t;
using ProfileToken = uint32_t;

enum class ProfileRoute : uint32_t {
    One = 1,
    Two = 2,
};

enum class ProfileDialogMessage : uint32_t {
    Initialize = 0x110,
    Command = 0x111,
};

enum class ProfileDialogControl : uint32_t {
    Confirm = 1,
    Cancel = 2,
    Remove = 0x43c,
    Create = 0x43d,
};

constexpr uint32_t ProfileRouteAddress = 0x5234bc;
constexpr uint32_t ProfileRouteHandlerSlot = 0x1e8;
constexpr uint32_t ModeQuerySlot = 0x10;
constexpr uint32_t FirstAllowedProfileMode = 5;
constexpr uint32_t SecondAllowedProfileMode = 2;
constexpr uint32_t ProfileDialogResourceAddress = 0x523c38;
constexpr uint32_t ProfileDialogProcedureAddress = 0x487a70;
constexpr uint32_t ApplicationAddress = 0x535910;
constexpr uint32_t ProfileEntrySelectionAddress = 0x53a96c;
constexpr uint32_t ProfileSelectionChangedAddress = 0x5362a4;
constexpr uint32_t ProfileSelectionNotification = 1;

// Gameplay keyboard cheat recognition, 0x424380 / 0x46ddc0.
constexpr uint32_t GameplayEscapeKey = 0x1b;
constexpr uint32_t WindowCommandMessage = 0x111;
constexpr uint32_t GameplayPauseCommand = 0x8080;
constexpr uint32_t GameplayInputTimeAddress = 0x535920;

// Text-list options and active mode checked by v1.3 command dispatch.
constexpr uint32_t AcknowledgementCheckCapacity = 1;
constexpr uint32_t AcknowledgementInsertHead = 2;
constexpr uint32_t AcknowledgementClearFirst = 4;
constexpr uint32_t CheatDispatchGameplayMode = 3;

// Version 1.3 contact registry embeds its name-to-metadata map at +0x10.
constexpr uint32_t ContactRegistryMapOffset = 0x10;
constexpr uint32_t ContactLogicAllocationBytes = 0x17c;
constexpr uint32_t ContactLogicVtable = 0x513f68;

// Lifecycle operation values and callback events from 0x4c7930 / 0x4d6590.
enum class SerializationOperation : uint32_t {
    CapturePeerIdentity = 3,
    WriteFields = 4,
    ReadFields = 7,
    ResolvePeerIdentity = 8,
};

enum class SerializationEvent : uint32_t {
    PeerIdentityCaptured = 0x50,
    FieldsWritten = 0x51,
    FieldsRead = 0x52,
    PeerIdentityResolved = 0x53,
};

constexpr uint32_t LifecycleNumericIdentityMapOffset = 0x48;

// Fixed-width stream operations observed at the raw actor/logic entries.
constexpr uint32_t RawStreamReadSlot = 0x2c;
constexpr uint32_t RawStreamWriteSlot = 0x30;
constexpr uint32_t RawStreamNameBytes = 0x80;
constexpr uint32_t RawStreamEmptyStringAddress = 0x52c668;

// Child base serializer transfers this original global DWORD.
constexpr uint32_t RawChildUnknownGlobalAddress = 0x5acd54;
constexpr uint32_t RawChildRestoredWord = 1001;

} // namespace v13
} // namespace recovered
} // namespace claw

#endif
