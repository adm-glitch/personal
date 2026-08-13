/// The 44-digit access key (*chave de acesso*) that identifies a Brazilian
/// fiscal document.
///
/// The layout is long-settled national spec, so it is safe to implement
/// directly (docs/PLAN.md §4):
///
///     cUF(2) AAMM(4) CNPJ(14) mod(2) série(3) nNF(9) tpEmis(1) cNF(8) cDV(1)
///
/// Everything here is derived from the digits alone — no network, no state
/// portal. That makes the whole type testable offline, which is why it is the
/// first thing built (M1).
///
/// The original digits are kept verbatim in ``raw``. Per the project's second
/// guiding principle, raw fiscal data is never discarded: the parsed fields are
/// a convenience layer over the string, not a replacement for it.
public struct AccessKey: Hashable, Sendable {

    /// Why a candidate string is not a valid access key.
    public enum ParseError: Error, Hashable, CustomStringConvertible {
        case wrongLength(expected: Int, actual: Int)
        case containsNonDigit(offset: Int)
        case checkDigitMismatch(computed: Int, stated: Int)

        public var description: String {
            switch self {
            case let .wrongLength(expected, actual):
                "access key must be \(expected) digits, got \(actual)"
            case let .containsNonDigit(offset):
                "access key contains a non-digit at offset \(offset)"
            case let .checkDigitMismatch(computed, stated):
                "check digit mismatch: computed \(computed), key states \(stated)"
            }
        }
    }

    /// Total digit count of a well-formed key.
    public static let length = 44

    /// `mod` value identifying a consumer electronic receipt (NFC-e).
    public static let modelNFCe = "65"
    /// `mod` value identifying a full electronic invoice (NF-e).
    public static let modelNFe = "55"
    /// `cUF` value for Pará — the only state in scope (docs/PLAN.md §1.3).
    public static let ufCodePara = "15"

    // MARK: Raw form

    /// The 44 digits exactly as they appeared, including leading zeros.
    public let raw: String

    // MARK: Decoded fields
    //
    // Fields where leading zeros carry meaning (CNPJ, numeric code) stay as
    // strings; genuinely numeric fields are exposed as integers.

    /// `cUF` — IBGE code of the issuing state. `"15"` is Pará.
    public let ufCode: String
    /// Four-digit emission year, widened from the key's two digits.
    public let emissionYear: Int
    /// Emission month, 1...12.
    public let emissionMonth: Int
    /// `CNPJ` — the issuer's 14-digit business registration, zeros preserved.
    public let issuerCNPJ: String
    /// `mod` — document model. See ``modelNFCe`` / ``modelNFe``.
    public let model: String
    /// `série` — document series.
    public let series: Int
    /// `nNF` — document number.
    public let number: Int
    /// `tpEmis` — emission type. `1` is normal online emission.
    public let emissionTypeCode: Int
    /// `cNF` — issuer-assigned numeric code, zeros preserved.
    public let numericCode: String
    /// `cDV` — the mod-11 check digit, already verified at init.
    public let checkDigit: Int

    // MARK: Derived

    /// Whether this key belongs to a consumer receipt rather than a full invoice.
    public var isNFCe: Bool { model == Self.modelNFCe }

    /// Whether the issuing state is Pará.
    ///
    /// Deliberately a single convenience rather than a 27-state table: the
    /// project supports one state, but keeps that fact from leaking into the
    /// purchase model (docs/PLAN.md D5).
    public var isPara: Bool { ufCode == Self.ufCodePara }

    /// Whether the receipt was issued in a contingency mode rather than online.
    ///
    /// Contingency receipts are worth singling out because the QR payload
    /// carries a different field set for them (docs/PLAN.md §4).
    public var isContingencyEmission: Bool { emissionTypeCode != 1 }

    /// The issuer's CNPJ in the conventional `NN.NNN.NNN/NNNN-NN` presentation.
    public var formattedIssuerCNPJ: String {
        let d = issuerCNPJ
        func part(_ lower: Int, _ upper: Int) -> String {
            let start = d.index(d.startIndex, offsetBy: lower)
            let end = d.index(d.startIndex, offsetBy: upper)
            return String(d[start..<end])
        }
        return "\(part(0, 2)).\(part(2, 5)).\(part(5, 8))/\(part(8, 12))-\(part(12, 14))"
    }

    // MARK: Parsing

    /// Parses and validates a 44-digit access key.
    ///
    /// Surrounding whitespace and the spaces or dots often used to group the
    /// digits for display are ignored. The check digit is verified, so a
    /// successfully constructed value is structurally sound.
    ///
    /// - Throws: ``ParseError`` when the length, alphabet, or check digit is wrong.
    public init(_ candidate: String) throws {
        let digits = candidate.filter { !" .\t\n-".contains($0) }

        guard digits.count == Self.length else {
            throw ParseError.wrongLength(expected: Self.length, actual: digits.count)
        }
        if let offset = digits.firstIndex(where: { !$0.isASCII || !$0.isNumber })
            .map({ digits.distance(from: digits.startIndex, to: $0) }) {
            throw ParseError.containsNonDigit(offset: offset)
        }

        // Fixed-width fields, consumed left to right in spec order.
        var cursor = digits.startIndex
        func take(_ width: Int) -> String {
            let end = digits.index(cursor, offsetBy: width)
            defer { cursor = end }
            return String(digits[cursor..<end])
        }

        let uf = take(2)
        let yearMonth = take(4)
        let cnpj = take(14)
        let mod = take(2)
        let serie = take(3)
        let nNF = take(9)
        let tpEmis = take(1)
        let cNF = take(8)
        let cDV = take(1)

        let stated = Int(cDV)!
        let computed = Self.checkDigit(forBody: String(digits.prefix(Self.length - 1)))
        guard computed == stated else {
            throw ParseError.checkDigitMismatch(computed: computed, stated: stated)
        }

        self.raw = digits
        self.ufCode = uf
        // The key carries only two year digits. NF-e began in 2006, so a
        // 2000-based window is unambiguous for every document that can exist.
        self.emissionYear = 2000 + Int(yearMonth.prefix(2))!
        self.emissionMonth = Int(yearMonth.suffix(2))!
        self.issuerCNPJ = cnpj
        self.model = mod
        self.series = Int(serie)!
        self.number = Int(nNF)!
        self.emissionTypeCode = Int(tpEmis)!
        self.numericCode = cNF
        self.checkDigit = stated
    }

    /// Computes the mod-11 check digit for the first 43 digits of a key.
    ///
    /// Digits are weighted 2...9 from right to left, cycling. A remainder of
    /// 0 or 1 yields a check digit of 0.
    ///
    /// Exposed because generating valid keys is genuinely useful in tests.
    public static func checkDigit(forBody body: String) -> Int {
        var sum = 0
        var weight = 2
        for character in body.reversed() {
            guard let digit = character.wholeNumberValue else { continue }
            sum += digit * weight
            weight = weight == 9 ? 2 : weight + 1
        }
        let remainder = sum % 11
        return remainder <= 1 ? 0 : 11 - remainder
    }
}

extension AccessKey: CustomStringConvertible {
    public var description: String { raw }
}
