// Draws the share card (og.jpg) and the app icons from the photos and the Literata font in web/.
// Run on a Mac when the look changes: swift pipeline/make_images.swift
// The card carries no brand name, so renaming the brand in site.config.yaml never needs a new card.
import AppKit
import CoreText

let root = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent().deletingLastPathComponent()
let web = root.appendingPathComponent("web")

func hex(_ s: String) -> CGColor {
    let v = Int(s.dropFirst(), radix: 16)!
    return CGColor(red: CGFloat((v >> 16) & 255) / 255, green: CGFloat((v >> 8) & 255) / 255, blue: CGFloat(v & 255) / 255, alpha: 1)
}
let ink = hex("#161616"), soft = hex("#5c5b58"), pink = hex("#e3ad9f"), red = hex("#b0533d"), blush = hex("#f5e4dd")

func font(_ size: CGFloat) -> CTFont {
    let url = web.appendingPathComponent("fonts/literata.woff2") as CFURL
    if let ds = CTFontManagerCreateFontDescriptorsFromURL(url) as? [CTFontDescriptor], let d = ds.first {
        let wght = 0x77676874 as NSNumber   // the variable font's weight axis, set to the site's 500
        let heavier = CTFontDescriptorCreateCopyWithAttributes(d, [kCTFontVariationAttribute: [wght: 500]] as CFDictionary)
        return CTFontCreateWithFontDescriptor(heavier, size, nil)
    }
    return CTFontCreateWithName("Georgia" as CFString, size, nil)
}

func canvas(_ w: Int, _ h: Int) -> CGContext {
    CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!,
              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
}

// text block, top-left anchored (CoreGraphics' origin is bottom-left)
func text(_ c: CGContext, _ s: String, _ size: CGFloat, _ color: CGColor, x: CGFloat, top: CGFloat, width: CGFloat, height: CGFloat, lineHeight: CGFloat) {
    var lh = lineHeight
    let style = withUnsafeBytes(of: &lh) { p -> CTParagraphStyle in
        let n = MemoryLayout<CGFloat>.size
        let para = [CTParagraphStyleSetting(spec: .minimumLineHeight, valueSize: n, value: p.baseAddress!),
                    CTParagraphStyleSetting(spec: .maximumLineHeight, valueSize: n, value: p.baseAddress!)]
        return para.withUnsafeBufferPointer { CTParagraphStyleCreate($0.baseAddress!, 2) }
    }
    let attr = NSAttributedString(string: s, attributes: [
        NSAttributedString.Key(kCTFontAttributeName as String): font(size),
        NSAttributedString.Key(kCTForegroundColorAttributeName as String): color,
        NSAttributedString.Key(kCTParagraphStyleAttributeName as String): style,
        NSAttributedString.Key(kCTKernAttributeName as String): -size * 0.02])
    let fs = CTFramesetterCreateWithAttributedString(attr)
    let H = CGFloat(c.height)
    let path = CGPath(rect: CGRect(x: x, y: H - top - height, width: width, height: height), transform: nil)
    CTFrameDraw(CTFramesetterCreateFrame(fs, CFRange(location: 0, length: 0), path, nil), c)
}

// the mark: three bars on pink, the tallest in facade red ("measured")
func mark(_ c: CGContext, x: CGFloat, y: CGFloat, size s: CGFloat) {
    let k = s / 64
    c.setFillColor(pink)
    c.addPath(CGPath(roundedRect: CGRect(x: x, y: y, width: s, height: s), cornerWidth: 14 * k, cornerHeight: 14 * k, transform: nil)); c.fillPath()
    for (bx, top, color) in [(14.0, 30.0, ink), (27.5, 20.0, ink), (41.0, 13.0, red)] {
        c.setFillColor(color)
        let r = CGRect(x: x + CGFloat(bx) * k, y: y + (64 - 50) * k, width: 9 * k, height: CGFloat(50 - top) * k)
        c.addPath(CGPath(roundedRect: r, cornerWidth: 1.5 * k, cornerHeight: 1.5 * k, transform: nil)); c.fillPath()
    }
}

func save(_ c: CGContext, _ name: String, jpeg: Bool = false) {
    let rep = NSBitmapImageRep(cgImage: c.makeImage()!)
    let data = jpeg ? rep.representation(using: .jpeg, properties: [.compressionFactor: 0.86])! : rep.representation(using: .png, properties: [:])!
    try! data.write(to: web.appendingPathComponent(name))
    print("wrote web/\(name)")
}

// ---------- og.jpg: the Hawa Mahal on the left, the promise on blush ----------
let og = canvas(1200, 630)
og.setFillColor(blush); og.fill(CGRect(x: 0, y: 0, width: 1200, height: 630))
if let src = NSImage(contentsOf: web.appendingPathComponent("img/hawa-mahal-sky-1600.jpg")), let img = src.cgImage(forProposedRect: nil, context: nil, hints: nil) {
    let w = 560.0, h = 630.0, iw = Double(img.width), ih = Double(img.height)
    let scale = max(w / iw, h / ih) * 1.7          // zoom in on the facade
    let cw = w / scale, ch = h / scale
    let crop = CGRect(x: (iw - cw) / 2, y: (ih - ch) * 0.92, width: cw, height: ch)   // the facade, not the sky
    og.draw(img.cropping(to: crop)!, in: CGRect(x: 0, y: 0, width: w, height: h))
}
mark(og, x: 616, y: 630 - 64 - 56, size: 56)
text(og, "Jaipur\u{2019}s industries, measured.", 64, ink, x: 616, top: 150, width: 560, height: 220, lineHeight: 68)
text(og, "Free data for the people who run them. One industry at a time.", 30, ink, x: 616, top: 392, width: 540, height: 100, lineHeight: 40)
text(og, "Cafés live \u{00B7} Jewellery next", 22, soft, x: 616, top: 548, width: 540, height: 40, lineHeight: 30)
save(og, "og.jpg", jpeg: true)

// ---------- icons ----------
for (size, name) in [(180, "apple-touch-icon.png"), (32, "favicon-32.png")] {
    let c = canvas(size, size)
    if size == 180 { c.setFillColor(pink); c.fill(CGRect(x: 0, y: 0, width: 180, height: 180)) }   // iOS rounds the corners itself
    mark(c, x: 0, y: 0, size: CGFloat(size))
    save(c, name)
}
