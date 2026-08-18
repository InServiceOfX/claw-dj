import AppKit
import Foundation

func fail(_ message: String) -> Never {
    fputs("error: \(message)\n", stderr)
    exit(1)
}

guard CommandLine.arguments.count == 5 else {
    fail("usage: render_teaser_card.swift INPUT.png OUTPUT.png TRANSITION_LABEL SERIES_LABEL")
}

let inputPath = CommandLine.arguments[1]
let outputPath = CommandLine.arguments[2]
let transitionLabel = CommandLine.arguments[3]
let seriesLabel = CommandLine.arguments[4]
let canvas = NSSize(width: 1080, height: 1920)

guard let source = NSImage(contentsOfFile: inputPath),
      source.size.width > 0,
      source.size.height > 0,
      let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: Int(canvas.width),
        pixelsHigh: Int(canvas.height),
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
      ) else {
    fail("could not load input or allocate output bitmap")
}

bitmap.size = canvas
NSGraphicsContext.saveGraphicsState()
guard let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
    fail("could not create graphics context")
}
NSGraphicsContext.current = context

NSColor.black.setFill()
NSBezierPath(rect: NSRect(origin: .zero, size: canvas)).fill()

let sourceRatio = source.size.width / source.size.height
let canvasRatio = canvas.width / canvas.height
let backgroundRect: NSRect
if sourceRatio > canvasRatio {
    let height = canvas.height
    let width = height * sourceRatio
    backgroundRect = NSRect(x: (canvas.width - width) / 2, y: 0, width: width, height: height)
} else {
    let width = canvas.width
    let height = width / sourceRatio
    backgroundRect = NSRect(x: 0, y: (canvas.height - height) / 2, width: width, height: height)
}
source.draw(in: backgroundRect, from: .zero, operation: .sourceOver, fraction: 0.42)
NSColor(calibratedWhite: 0.0, alpha: 0.42).setFill()
NSBezierPath(rect: NSRect(origin: .zero, size: canvas)).fill()

let foregroundWidth: CGFloat = 1000
let foregroundHeight = foregroundWidth / sourceRatio
let foregroundRect = NSRect(
    x: (canvas.width - foregroundWidth) / 2,
    y: (canvas.height - foregroundHeight) / 2,
    width: foregroundWidth,
    height: foregroundHeight
)
NSColor(calibratedWhite: 1.0, alpha: 0.9).setStroke()
let border = NSBezierPath(rect: foregroundRect.insetBy(dx: -8, dy: -8))
border.lineWidth = 8
border.stroke()
source.draw(in: foregroundRect, from: .zero, operation: .sourceOver, fraction: 1.0)

NSColor(calibratedWhite: 0.0, alpha: 0.52).setFill()
NSBezierPath(rect: NSRect(x: 0, y: 1605, width: canvas.width, height: 260)).fill()
NSBezierPath(rect: NSRect(x: 0, y: 210, width: canvas.width, height: 300)).fill()

func drawCentered(_ text: String, y: CGFloat, height: CGFloat, size: CGFloat, kern: CGFloat = 1.2) {
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = .center
    paragraph.lineBreakMode = .byWordWrapping
    let shadow = NSShadow()
    shadow.shadowColor = NSColor(calibratedWhite: 0.0, alpha: 0.9)
    shadow.shadowBlurRadius = 6
    shadow.shadowOffset = NSSize(width: 3, height: -3)
    let attributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.boldSystemFont(ofSize: size),
        .foregroundColor: NSColor.white,
        .paragraphStyle: paragraph,
        .shadow: shadow,
        .kern: kern
    ]
    NSAttributedString(string: text, attributes: attributes).draw(
        in: NSRect(x: 40, y: y, width: canvas.width - 80, height: height)
    )
}

/// Long "A → B" labels must fit fully (e.g. BIG DADDY KANE). Prefer an
/// explicit two-line split on the arrow; otherwise shrink until the box fits.
func drawTransitionLabel(_ text: String, y: CGFloat, height: CGFloat) {
    let maxWidth = canvas.width - 80
    let display: String
    if let arrow = text.range(of: " → ") {
        let left = String(text[..<arrow.lowerBound]).trimmingCharacters(in: .whitespaces)
        let right = String(text[arrow.upperBound...]).trimmingCharacters(in: .whitespaces)
        display = "\(left)\n→  \(right)"
    } else if let arrow = text.range(of: "->") {
        let left = String(text[..<arrow.lowerBound]).trimmingCharacters(in: .whitespaces)
        let right = String(text[arrow.upperBound...]).trimmingCharacters(in: .whitespaces)
        display = "\(left)\n→  \(right)"
    } else {
        display = text
    }

    var size: CGFloat = 52
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = .center
    paragraph.lineBreakMode = .byWordWrapping
    while size >= 34 {
        let attributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.boldSystemFont(ofSize: size),
            .paragraphStyle: paragraph,
            .kern: 0.8
        ]
        let bounds = (display as NSString).boundingRect(
            with: NSSize(width: maxWidth, height: .greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin, .usesFontLeading],
            attributes: attributes
        )
        if bounds.height <= height - 4 {
            break
        }
        size -= 2
    }
    drawCentered(display, y: y, height: height, size: size, kern: 0.8)
}

drawCentered("CLAW-DJ", y: 1740, height: 105, size: 86)
drawCentered("THROWBACK R&B + HIP-HOP", y: 1640, height: 70, size: 46)
// Taller box so "BIG DADDY KANE" is never clipped to "BIG"
drawTransitionLabel(transitionLabel, y: 330, height: 150)
drawCentered(seriesLabel, y: 250, height: 62, size: 40)
drawCentered("FULL MIX ON YOUTUBE  •  @claw-dj", y: 195, height: 50, size: 32)

context.flushGraphics()
NSGraphicsContext.restoreGraphicsState()

guard let png = bitmap.representation(using: .png, properties: [:]) else {
    fail("could not encode PNG")
}

do {
    try png.write(to: URL(fileURLWithPath: outputPath), options: .atomic)
    print(outputPath)
} catch {
    fail("could not write output: \(error)")
}
