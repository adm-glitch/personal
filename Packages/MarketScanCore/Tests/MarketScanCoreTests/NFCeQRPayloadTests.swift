import Testing
@testable import MarketScanCore

@Suite("NFCeQRPayload")
struct NFCeQRPayloadTests {

    @Test("parses the QR from a real Belém receipt")
    func parsesRealQR() throws {
        let payload = try NFCeQRPayload(qrContents: Fixture.realQR)

        #expect(payload.host == "appnfc.sefa.pa.gov.br")
        #expect(payload.path == "/portal/view/consultas/nfce/nfceForm.seam")
        #expect(payload.accessKey.raw == Fixture.realKey)
        #expect(payload.qrVersion == "2")
        #expect(payload.environment == .production)
        #expect(payload.fields.count == 5)
        #expect(payload.cIdToken == "1")
        #expect(payload.hash == "44772474E995A5D08E243CFB0DC51279C5E6AE9D")
        #expect(payload.isLayoutConfirmed)
        #expect(payload.layout == .version2Online(
            cIdToken: "1",
            hash: "44772474E995A5D08E243CFB0DC51279C5E6AE9D"
        ))
    }

    @Test("keeps the raw payload and source URL verbatim")
    func preservesRawForm() throws {
        let payload = try NFCeQRPayload(qrContents: Fixture.realQR)

        // Never discard raw fiscal data (docs/PLAN.md §1.2): the decoded
        // fields must be reconstructible from what we kept.
        #expect(payload.sourceURL == Fixture.realQR)
        #expect(payload.rawPayload == payload.fields.joined(separator: "|"))
        #expect(payload.rawPayload.hasPrefix(Fixture.realKey))
        #expect(!payload.rawPayload.contains("%7C"))
    }

    @Test("accepts pipes literal as well as percent-encoded")
    func acceptsLiteralPipes() throws {
        let literal = Fixture.realQR.replacingOccurrences(of: "%7C", with: "|")
        let fromLiteral = try NFCeQRPayload(qrContents: literal)
        let fromEncoded = try NFCeQRPayload(qrContents: Fixture.realQR)

        #expect(fromLiteral.fields == fromEncoded.fields)
        #expect(fromLiteral.accessKey == fromEncoded.accessKey)
    }

    @Test("tolerates surrounding whitespace from copy/paste")
    func toleratesWhitespace() throws {
        let padded = "  \(Fixture.realQR)\n"
        #expect(try NFCeQRPayload(qrContents: padded).accessKey.raw == Fixture.realKey)
    }

    @Test("reads tpAmb as the issuing environment")
    func decodesEnvironment() throws {
        func environment(tpAmb: String) throws -> NFCeQRPayload.Environment {
            let qr = Fixture.realQR.replacingOccurrences(
                of: "%7C2%7C1%7C1%7C",
                with: "%7C2%7C\(tpAmb)%7C1%7C"
            )
            return try NFCeQRPayload(qrContents: qr).environment
        }

        #expect(try environment(tpAmb: "1") == .production)
        #expect(try environment(tpAmb: "2") == .homologation)
        // An unexpected value stays visible rather than being coerced.
        #expect(try environment(tpAmb: "7") == .other("7"))
    }

    @Test("refuses to name fields in a layout we have not confirmed")
    func unverifiedLayoutIsNotGuessed() throws {
        // A 10-field payload resembling the older QR version 1 arrangement.
        // We have no real receipt for it, so nothing should be named.
        let extra = ["2", "1", "", "2026-08-12T10:00:00-03:00", "123.45", "9.99", "abc", "1", "DEADBEEF"]
        let qr = "https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/nfceForm.seam?p="
            + ([Fixture.realKey] + extra).joined(separator: "%7C")

        let payload = try NFCeQRPayload(qrContents: qr)

        #expect(payload.layout == .unverified(fieldCount: 10))
        #expect(!payload.isLayoutConfirmed)
        #expect(payload.cIdToken == nil)
        #expect(payload.hash == nil)
        // The fields the spec puts first are stable across versions, and
        // everything else is still there to inspect.
        #expect(payload.accessKey.raw == Fixture.realKey)
        #expect(payload.qrVersion == "2")
        #expect(payload.fields.count == 10)
        #expect(payload.fields[3] == "")
    }

    @Test("uses the last p parameter when one is duplicated")
    func duplicatedParameterTakesLast() throws {
        let other = Fixture.key(settingOffset: Fixture.tpEmisOffset, to: "9")
        let qr = "https://appnfc.sefa.pa.gov.br/x.seam?p=\(Fixture.realKey)%7C2%7C1%7C1%7CAA"
            + "&p=\(other)%7C2%7C1%7C1%7CBB"

        #expect(try NFCeQRPayload(qrContents: qr).accessKey.raw == other)
    }

    @Test("rejects contents that are not a consultation URL")
    func rejectsNonURL() {
        #expect(throws: NFCeQRPayload.ParseError.notAURL) {
            try NFCeQRPayload(qrContents: "   ")
        }
        // No query string at all.
        #expect(throws: NFCeQRPayload.ParseError.missingPParameter) {
            try NFCeQRPayload(qrContents: "https://appnfc.sefa.pa.gov.br/portal")
        }
        // Query present but no host.
        #expect(throws: NFCeQRPayload.ParseError.notAURL) {
            try NFCeQRPayload(qrContents: "not-a-url?p=\(Fixture.realKey)%7C2%7C1")
        }
    }

    @Test("rejects a URL whose p parameter is missing or empty")
    func rejectsMissingPayload() {
        #expect(throws: NFCeQRPayload.ParseError.missingPParameter) {
            try NFCeQRPayload(qrContents: "https://appnfc.sefa.pa.gov.br/x.seam?q=1")
        }
        #expect(throws: NFCeQRPayload.ParseError.emptyPayload) {
            try NFCeQRPayload(qrContents: "https://appnfc.sefa.pa.gov.br/x.seam?p=")
        }
    }

    @Test("rejects a payload with too few fields to interpret")
    func rejectsTruncatedPayload() {
        #expect(throws: NFCeQRPayload.ParseError.tooFewFields(count: 2)) {
            try NFCeQRPayload(qrContents: "https://appnfc.sefa.pa.gov.br/x.seam?p=\(Fixture.realKey)%7C2")
        }
    }

    @Test("surfaces an invalid access key rather than swallowing it")
    func rejectsBadAccessKey() {
        let corrupted = String(Fixture.realKey.dropLast() + "1")
        #expect(throws: NFCeQRPayload.ParseError.invalidAccessKey(
            .checkDigitMismatch(computed: 0, stated: 1)
        )) {
            try NFCeQRPayload(qrContents: "https://appnfc.sefa.pa.gov.br/x.seam?p=\(corrupted)%7C2%7C1%7C1%7CAA")
        }
    }
}
