import Foundation

/// The contents of the QR code printed on an NFC-e receipt.
///
/// The QR encodes a consultation URL whose `p` query parameter is a
/// pipe-delimited payload. Interpreting it is purely local work — this type
/// never fetches anything (docs/PLAN.md D2).
///
/// ## On not guessing layouts
///
/// The field set of `p` varies by QR version and by whether the receipt was
/// issued online or in contingency, and the governing technical note has been
/// revised more than once. docs/PLAN.md §4 is explicit that the layout must be
/// read off real receipts rather than recalled.
///
/// So this parser names fields only for a layout we have actually seen on a
/// Belém receipt, and represents anything else as
/// ``Layout/unverified(fieldCount:)`` — still fully preserved in ``fields``,
/// but with no invented field names. When a contingency receipt turns up, add
/// a case; do not stretch an existing one to fit.
public struct NFCeQRPayload: Hashable, Sendable {

    /// Why a candidate QR string is not a usable NFC-e payload.
    public enum ParseError: Error, Hashable, CustomStringConvertible {
        case notAURL
        case missingPParameter
        case emptyPayload
        case tooFewFields(count: Int)
        case invalidAccessKey(AccessKey.ParseError)

        public var description: String {
            switch self {
            case .notAURL:
                "QR contents are not a URL"
            case .missingPParameter:
                "consultation URL has no 'p' query parameter"
            case .emptyPayload:
                "'p' parameter is empty"
            case let .tooFewFields(count):
                "'p' has \(count) field(s); the access key, version and environment are the minimum"
            case let .invalidAccessKey(underlying):
                "first 'p' field is not a valid access key: \(underlying)"
            }
        }
    }

    /// `tpAmb` — which SEFAZ environment issued the document.
    public enum Environment: Hashable, Sendable {
        case production
        case homologation
        /// Preserved rather than rejected, so an unexpected value stays visible.
        case other(String)

        init(code: String) {
            switch code {
            case "1": self = .production
            case "2": self = .homologation
            default: self = .other(code)
            }
        }
    }

    /// Which documented field arrangement the payload matches.
    public enum Layout: Hashable, Sendable {
        /// `chNFe|nVersao|tpAmb|cIdToken|cHashQRCode`
        ///
        /// Confirmed against a real Belém supermarket receipt on 2026-08-13
        /// (QR version 2, normal online emission).
        case version2Online(cIdToken: String, hash: String)

        /// A field count not yet observed on a real receipt.
        ///
        /// Raw fields remain available in ``NFCeQRPayload/fields``. Nothing is
        /// assigned a name, because assigning the wrong name silently is worse
        /// than assigning none.
        case unverified(fieldCount: Int)
    }

    // MARK: Raw form

    /// The QR contents exactly as scanned.
    public let sourceURL: String
    /// Host the QR points at, lowercased. Pará's is `appnfc.sefa.pa.gov.br`.
    public let host: String
    /// Path component of the consultation URL.
    public let path: String
    /// The `p` parameter, percent-decoding undone, before splitting.
    public let rawPayload: String
    /// Every pipe-delimited field, in order, with nothing dropped.
    public let fields: [String]

    // MARK: Decoded fields

    /// `chNFe` — the access key, already validated.
    public let accessKey: AccessKey
    /// `nVersao` — QR code layout version, as written.
    public let qrVersion: String
    /// `tpAmb` — issuing environment.
    public let environment: Environment
    /// Which documented layout the field count matched.
    public let layout: Layout

    // MARK: Derived

    /// `cIdToken` — identifies which contributor security code signed the QR.
    /// `nil` for layouts we have not confirmed.
    public var cIdToken: String? {
        if case let .version2Online(cIdToken, _) = layout { return cIdToken }
        return nil
    }

    /// `cHashQRCode` — the QR's signature.
    ///
    /// Cannot be verified locally: it is computed with the issuer's secret
    /// contributor security code (CSC), which we do not hold. Preserved as
    /// evidence and because the portal expects it echoed back.
    public var hash: String? {
        if case let .version2Online(_, hash) = layout { return hash }
        return nil
    }

    /// Whether the layout is one we have confirmed against a real receipt.
    public var isLayoutConfirmed: Bool {
        if case .unverified = layout { return false }
        return true
    }

    // MARK: Parsing

    /// Parses the contents of a scanned NFC-e QR code.
    ///
    /// Accepts the `p` value with pipes either literal or percent-encoded as
    /// `%7C`, since the two forms both occur depending on how the URL was
    /// copied out of a scanner.
    ///
    /// - Throws: ``ParseError`` when the URL, the `p` parameter, or the
    ///   embedded access key is unusable.
    public init(qrContents: String) throws {
        let trimmed = qrContents.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { throw ParseError.notAURL }

        // Split the query off by hand rather than via URL/URLComponents: a raw
        // payload can contain an unencoded '|', which is not a legal URL
        // character and makes strict parsers reject the whole string.
        let parts = trimmed.split(separator: "?", maxSplits: 1, omittingEmptySubsequences: false)
        guard parts.count == 2 else { throw ParseError.missingPParameter }

        let base = String(parts[0])
        let query = String(parts[1])

        guard let scheme = base.range(of: "://") else { throw ParseError.notAURL }
        let afterScheme = base[scheme.upperBound...]
        let slash = afterScheme.firstIndex(of: "/")
        self.host = String(slash.map { afterScheme[..<$0] } ?? afterScheme).lowercased()
        self.path = String(slash.map { afterScheme[$0...] } ?? "")
        guard !host.isEmpty else { throw ParseError.notAURL }

        // Find 'p' among the query parameters. Take the last occurrence, which
        // is what a server reading a duplicated parameter would typically use.
        var pValue: String?
        for pair in query.split(separator: "&", omittingEmptySubsequences: true) {
            let kv = pair.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
            guard kv.count == 2, kv[0] == "p" else { continue }
            pValue = String(kv[1])
        }
        guard let encoded = pValue else { throw ParseError.missingPParameter }
        guard !encoded.isEmpty else { throw ParseError.emptyPayload }

        // '+' is not a separator here; only percent-decoding applies.
        let payload = encoded.removingPercentEncoding ?? encoded
        guard !payload.isEmpty else { throw ParseError.emptyPayload }
        self.rawPayload = payload
        self.sourceURL = trimmed

        let split = payload.split(separator: "|", omittingEmptySubsequences: false).map(String.init)
        self.fields = split
        guard split.count >= 3 else { throw ParseError.tooFewFields(count: split.count) }

        do {
            self.accessKey = try AccessKey(split[0])
        } catch let error as AccessKey.ParseError {
            throw ParseError.invalidAccessKey(error)
        }
        self.qrVersion = split[1]
        self.environment = Environment(code: split[2])

        switch split.count {
        case 5:
            self.layout = .version2Online(cIdToken: split[3], hash: split[4])
        default:
            self.layout = .unverified(fieldCount: split.count)
        }
    }
}
