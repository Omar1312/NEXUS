# macOS code signing and notarization

The ordinary macOS build workflow produces unsigned development artifacts. The manually dispatched approved-release workflow runs `scripts/release_macos.sh`; it requires signing and notarization secrets and fails closed when they are missing. Do not claim otherwise and do not ask users to disable Gatekeeper.

For public direct distribution, prepare a Developer ID Application identity and App Store Connect API key. Store these GitHub Actions secrets: `NEXUS_MACOS_CERT_P12_BASE64`, `NEXUS_MACOS_CERT_PASSWORD`, `NEXUS_MACOS_SIGNING_IDENTITY`, `NEXUS_APPLE_API_KEY_BASE64`, `NEXUS_APPLE_API_KEY_ID`, and `NEXUS_APPLE_API_ISSUER_ID`. The script creates an ephemeral keychain, signs the app with hardened runtime and timestamp, submits/staples the DMG, verifies the signature/notarization, then deletes the temporary keychain. The app requests no entitlements. The script has not been run because this checkout has no Apple credentials or macOS runner.

`Prepare and publish approved release` builds signed ARM64 and Intel DMGs, then can create a GitHub Release only when its dispatch input is exactly `PUBLISH`. Without all secrets, signing fails and the publish job cannot proceed. Review artifacts and obtain project-owner approval before dispatching with that confirmation value.

Apple states that Developer ID identifies software distributed outside the Mac App Store and recommends notarization for outside-store distribution. A paid Apple Developer Program membership is typically required to obtain Developer ID distribution credentials; confirm current enrollment and pricing directly with Apple before committing to the cost. No enrollment or paid service was initiated.

References: [Developer ID](https://developer.apple.com/developer-id/), [notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution/), [distribution](https://developer.apple.com/documentation/technologyoverviews/distribution).
