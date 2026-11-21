// Offline Apple Vision OCR helper. JSON lines in/out; no game/network access.
import Foundation
import Vision

struct Input: Decodable { let image: String; let correction: Bool? }
struct Row: Encodable { let text: String; let confidence: Float }
struct Output: Encodable { let rows: [Row]; let error: String? }
let decoder = JSONDecoder()
let encoder = JSONEncoder()
while let line = readLine() {
    autoreleasepool {
        let output: Output
        do {
            guard line.utf8.count <= 8_000_000 else { throw NSError(domain: "input", code: 1) }
            let input = try decoder.decode(Input.self, from: Data(line.utf8))
            guard let image = Data(base64Encoded: input.image) else { throw NSError(domain: "image", code: 1) }
            let request = VNRecognizeTextRequest()
            request.revision = VNRecognizeTextRequestRevision3
            request.recognitionLevel = .accurate
            request.recognitionLanguages = ["ja-JP", "en-US"]
            request.usesLanguageCorrection = input.correction ?? true
            if request.usesLanguageCorrection {
                request.customWords = ["ピカチュウ", "ベベノム", "タイプ：ヌル", "タイプ:ヌル", "タイプヌル", "サトシ", "受け取った", "うけとった", "もらった", "PUSH", "START", "BUTTON"]
            }
            try VNImageRequestHandler(data: image, options: [:]).perform([request])
            let rows = (request.results ?? []).compactMap { result -> Row? in
                guard let candidate = result.topCandidates(1).first else { return nil }
                return Row(text: candidate.string, confidence: candidate.confidence)
            }
            output = Output(rows: rows, error: nil)
        } catch {
            output = Output(rows: [], error: String(describing: error))
        }
        if let data = try? encoder.encode(output), let json = String(data: data, encoding: .utf8) {
            print(json)
            fflush(stdout)
        }
    }
}
