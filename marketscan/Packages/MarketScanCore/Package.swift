// swift-tools-version: 6.0
import PackageDescription

// Core logic lives here, deliberately free of Apple-UI dependencies so it
// builds and tests on Linux as well as macOS (docs/PLAN.md D1, D2, D3).
// The iOS app target is a thin shell that depends on this package.
let package = Package(
    name: "MarketScanCore",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .library(name: "MarketScanCore", targets: ["MarketScanCore"]),
    ],
    targets: [
        .target(name: "MarketScanCore"),
        // Fixture wiring lands with the HTML parser at M3; M1's tests are
        // driven by the captured QR payloads inline.
        .testTarget(
            name: "MarketScanCoreTests",
            dependencies: ["MarketScanCore"]
        ),
    ]
)
