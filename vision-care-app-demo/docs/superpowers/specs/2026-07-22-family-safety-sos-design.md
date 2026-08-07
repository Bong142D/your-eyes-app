# Family / An Toàn & SOS screen — design

Date: 2026-07-22

## Goal

Add a new "An Toàn & SOS" screen (safety + SOS) matching the supplied mockup image, re-themed to the existing light Your Eyes palette (mint/cyan/navy, `YourEyesMockup.tsx`). Static mock data only — no backend, no real geolocation, no real gesture-hold logic. Purely a UI showcase, same fidelity level as the other 10 screens already in the poster board.

## Scope decisions (confirmed with user)

- Re-theme the dark mockup to the existing light palette (`C` tokens in `YourEyesMockup.tsx`) — do not introduce a second dark theme.
- Add a real bottom tab bar (expo-router `Tabs`), 5 tabs: Home, Features, Family, Community, Profile.
- Only **Family** (the An Toàn & SOS screen) gets full detail. The other 4 tabs are placeholder screens ("Sắp ra mắt") to be filled in later.
- Mock data hardcoded in the new source file, same pattern as `plans`, `transactions`, etc. in `YourEyesMockup.tsx`.

## Routing

New route group `app/main/(tabs)/` — chosen specifically to avoid colliding with the existing `app/index.tsx` (`/`, currently `WelcomeScreen`). Group segments `(tabs)` don't appear in the URL, so:

- `app/main/(tabs)/_layout.tsx` → Tabs layout (5 tabs)
- `app/main/(tabs)/index.tsx` → `/main` — Home placeholder
- `app/main/(tabs)/features.tsx` → `/main/features` — placeholder
- `app/main/(tabs)/family.tsx` → `/main/family` — **An Toàn & SOS screen (full detail)**
- `app/main/(tabs)/community.tsx` → `/main/community` — placeholder
- `app/main/(tabs)/profile.tsx` → `/main/profile` — placeholder

Tab bar icons (lucide-react-native): `Home`, `Sparkles` (Features), `Users` (Family), `Users2` (Community), `User` (Profile). Active tab: cyan icon/label on a mint pill background behind the icon, matching the reference image's active-tab treatment. Inactive: `C.muted`.

## Shared code changes

`src/YourEyesMockup.tsx`: export the module-private tokens/components needed by the new file instead of duplicating them — `C`, `S`, `R`, `softShadow`, `ScreenShell`, `RowCard`, `SectionLabel`. No visual or behavioral change to existing screens.

## New file: `src/SafetyMockup.tsx`

Exports:
- `SafetyScreen({ preview })` — the An Toàn & SOS screen
- `PlaceholderScreen({ title })` — reused by the 4 stub tabs
- Mock data consts: `quickCalls`, `currentLocation`, `activityLog`

### SafetyScreen layout (top to bottom, inside `ScreenShell title="AN TOÀN"`)

1. **SOS button** — big rounded card, `LinearGradient` light-red → `C.danger`, centered asterisk icon (lucide `Asterisk` or `Plus`-style) + "SOS" bold white text. Below the card (outside, muted caption): "Giữ 3 giây để báo động". Static — no hold-gesture wiring (out of scope, same as every other button in the mockup set).
2. **"Gọi nhanh"** section label + 3 `RowCard`s from mock `quickCalls`: Gọi Mẹ, Gọi Anh (icon `Phone`, tone `C.cyan`), Gọi 115 (icon emergency/plus, tone `C.danger`, red-tinted border to stand out like the reference).
3. **"Theo dõi"** section label:
   - Location card: pin icon + "VỊ TRÍ HIỆN TẠI" label + address (mock string), divider, status row ("Đang di chuyển" in `C.success` + "2 phút trước" muted).
   - Activity log card: "NHẬT KÝ HOẠT ĐỘNG HÔM NAY" label + list of mock entries, each with icon (check-circle done / footprints in-progress), title, time.

All mock data lives in `SafetyMockup.tsx` as plain arrays/objects, no async/fetch.

## Poster board integration

`YourEyesMockup.tsx`: add an 11th entry to `routeCards` ("An Toàn & SOS", href `/main/family`) and the matching component to the `previews` array so it shows in the preview grid like the other 10 screens.

## Out of scope

- Real navigation/auth guarding for the new tab group
- Real SOS hold-to-trigger gesture, real phone dialing, real geolocation/tracking
- Content for Home/Features/Community/Profile beyond a placeholder
- Any backend/API integration
