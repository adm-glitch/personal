import Testing
@testable import MarketScanCore

/// Shared fixture data, kept in one place so both test suites agree on it.
enum Fixture {
    /// Access key from `Fixtures/para/qr/receipt-01.txt` — a real Belém
    /// supermarket receipt, August 2026.
    static let realKey = "15260831671814000858651020005478671102541020"

    /// The full QR contents of the same receipt, pipes percent-encoded as the
    /// iPhone Camera app hands them over.
    static let realQR = """
        https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/nfceForm.seam\
        ?p=15260831671814000858651020005478671102541020%7C2%7C1%7C1\
        %7C44772474E995A5D08E243CFB0DC51279C5E6AE9D
        """

    /// Rebuilds a key with one digit replaced, fixing up the check digit so the
    /// result is still structurally valid. Lets us exercise field combinations
    /// we have no real receipt for.
    static func key(_ base: String = realKey, settingOffset offset: Int, to digit: Character) -> String {
        var body = Array(base.prefix(43))
        body[offset] = digit
        let rebuilt = String(body)
        return rebuilt + String(AccessKey.checkDigit(forBody: rebuilt))
    }

    /// Offset of `tpEmis`: cUF(2) + AAMM(4) + CNPJ(14) + mod(2) + série(3) + nNF(9).
    static let tpEmisOffset = 34
    /// Offset of `mod`: cUF(2) + AAMM(4) + CNPJ(14).
    static let modOffset = 20
}

@Suite("AccessKey")
struct AccessKeyTests {

    @Test("decodes every field of a real Pará NFC-e key")
    func decodesRealKey() throws {
        let key = try AccessKey(Fixture.realKey)

        #expect(key.raw == Fixture.realKey)
        #expect(key.ufCode == "15")
        #expect(key.emissionYear == 2026)
        #expect(key.emissionMonth == 8)
        #expect(key.issuerCNPJ == "31671814000858")
        #expect(key.model == "65")
        #expect(key.series == 102)
        #expect(key.number == 547_867)
        #expect(key.emissionTypeCode == 1)
        #expect(key.numericCode == "10254102")
        #expect(key.checkDigit == 0)
    }

    @Test("derives the flags the app actually branches on")
    func derivedFlags() throws {
        let key = try AccessKey(Fixture.realKey)

        #expect(key.isNFCe)
        #expect(key.isPara)
        #expect(!key.isContingencyEmission)
        #expect(key.formattedIssuerCNPJ == "31.671.814/0008-58")
        #expect(key.description == Fixture.realKey)
    }

    @Test("recognises a contingency emission")
    func contingencyEmission() throws {
        let contingency = Fixture.key(settingOffset: Fixture.tpEmisOffset, to: "9")
        let key = try AccessKey(contingency)

        #expect(key.emissionTypeCode == 9)
        #expect(key.isContingencyEmission)
    }

    @Test("distinguishes NFC-e from a full NF-e")
    func documentModel() throws {
        // mod is "65" for NFC-e; the leading digit is what distinguishes "55".
        let invoice = Fixture.key(settingOffset: Fixture.modOffset, to: "5")
        let key = try AccessKey(invoice)

        #expect(key.model == "55")
        #expect(!key.isNFCe)
    }

    @Test("check digit matches the mod-11 weighting")
    func checkDigitComputation() {
        let body = String(Fixture.realKey.prefix(43))
        #expect(AccessKey.checkDigit(forBody: body) == 0)
    }

    @Test("a remainder of 0 or 1 yields a check digit of zero")
    func checkDigitEdgeCases() {
        // 43 zeros weight to a sum of 0, remainder 0.
        #expect(AccessKey.checkDigit(forBody: String(repeating: "0", count: 43)) == 0)
    }

    @Test("ignores the grouping characters used for display")
    func toleratesFormatting() throws {
        let spaced = Fixture.realKey.enumerated()
            .map { $0.offset % 4 == 0 && $0.offset > 0 ? " \($0.element)" : String($0.element) }
            .joined()
        #expect(try AccessKey(spaced).raw == Fixture.realKey)
        #expect(try AccessKey("  \(Fixture.realKey)\n").raw == Fixture.realKey)
    }

    @Test("rejects a key of the wrong length")
    func rejectsWrongLength() {
        #expect(throws: AccessKey.ParseError.wrongLength(expected: 44, actual: 43)) {
            try AccessKey(String(Fixture.realKey.prefix(43)))
        }
        #expect(throws: AccessKey.ParseError.wrongLength(expected: 44, actual: 0)) {
            try AccessKey("")
        }
    }

    @Test("rejects a key containing a non-digit")
    func rejectsNonDigit() {
        let corrupted = "X" + Fixture.realKey.dropFirst()
        #expect(throws: AccessKey.ParseError.containsNonDigit(offset: 0)) {
            try AccessKey(corrupted)
        }
    }

    @Test("rejects a key whose check digit does not match")
    func rejectsBadCheckDigit() {
        // Real key with the stated check digit bumped 0 -> 1.
        let corrupted = Fixture.realKey.dropLast() + "1"
        #expect(throws: AccessKey.ParseError.checkDigitMismatch(computed: 0, stated: 1)) {
            try AccessKey(String(corrupted))
        }
    }

    @Test("a single transposed digit fails validation")
    func catchesTransposition() throws {
        // Mod-11 exists to catch exactly this, so assert it actually does.
        var digits = Array(Fixture.realKey)
        let i = 6, j = 7
        #expect(digits[i] != digits[j], "pick two differing digits for the swap to mean anything")
        digits.swapAt(i, j)
        #expect(throws: (any Error).self) { try AccessKey(String(digits)) }
    }
}
