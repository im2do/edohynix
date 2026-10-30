import Foundation
import PDFKit

// Native macOS fallback. Text extraction only; no OCR or remote service.
guard CommandLine.arguments.count == 2,
      let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])),
      !doc.isLocked else {
    fputs("PDF 열기 실패 또는 잠긴 PDF\n", stderr)
    exit(2)
}
let pages = (0..<doc.pageCount).map { index -> [String: Any] in
    ["page": index + 1, "text": doc.page(at: index)?.string ?? ""]
}
let data = try JSONSerialization.data(withJSONObject: ["page_count": doc.pageCount, "pages": pages])
FileHandle.standardOutput.write(data)
