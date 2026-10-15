"""Minimal AppKit subtitle window driven by JSON lines on stdin."""

from __future__ import annotations

import argparse
import json
import sys
import threading

from AppKit import (
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSColor,
    NSFont,
    NSMakeRect,
    NSMakeSize,
    NSScreen,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject
from objc import python_method


class SubtitleController(NSObject):
    def applicationDidFinishLaunching_(self, notification):  # noqa: N802
        del notification
        screen = NSScreen.mainScreen().visibleFrame()
        width, height = 768, 720
        rect = NSMakeRect(
            screen.origin.x + (screen.size.width - width) / 2,
            screen.origin.y + 24,
            width,
            height,
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
            | NSWindowStyleMaskResizable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("NES Translation Mirror")
        self.window.setLevel_(3)
        self.window.setBackgroundColor_(NSColor.blackColor())
        self.window.setContentAspectRatio_(NSMakeSize(256, 240))
        self.window.setDelegate_(self)
        self.drawFields = []
        self.latestCommand = {"visible": False}
        self.window.orderFrontRegardless()
        threading.Thread(target=self._read_commands, daemon=True).start()

    @python_method
    def _read_commands(self):
        for line in sys.stdin:
            try:
                command = json.loads(line)
            except (ValueError, TypeError):
                continue
            payload = json.dumps(command, ensure_ascii=False)
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "applyState:", payload, False
            )
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "finish:", None, False
        )

    def applyState_(self, payload):  # noqa: N802
        self.latestCommand = json.loads(payload)
        self._render()

    def windowDidResize_(self, notification):  # noqa: N802
        del notification
        self._render()

    @python_method
    def _field(self, text, ppu_bounds, font_size):
        bounds = self.window.contentView().bounds()
        scale_x = bounds.size.width / 256.0
        scale_y = bounds.size.height / 240.0
        source_width = ppu_bounds["width"]
        # A two-tile NES word can be narrower than two AppKit CJK glyphs once
        # normal text-field padding is included. Expand only the presentation
        # rectangle, while retaining the source rectangle's centre.
        display_width = max(source_width, len(text) * (font_size + 4.0))
        display_x = max(
            0.0, min(256.0 - display_width,
                     ppu_bounds["x"] - (display_width - source_width) / 2.0)
        )
        x = display_x * scale_x
        y = bounds.size.height - (
            ppu_bounds["y"] + ppu_bounds["height"]
        ) * scale_y
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(
            x, y, display_width * scale_x,
            ppu_bounds["height"] * scale_y,
        ))
        field.setEditable_(False)
        field.setSelectable_(False)
        field.setBezeled_(False)
        field.setDrawsBackground_(True)
        field.setBackgroundColor_(NSColor.blackColor())
        field.setTextColor_(NSColor.whiteColor())
        field.setFont_(NSFont.systemFontOfSize_(font_size * scale_y))
        field.setAlignment_(1)
        field.setMaximumNumberOfLines_(0)
        field.setStringValue_(text)
        self.window.contentView().addSubview_(field)
        self.drawFields.append(field)

    @python_method
    def _debug_region(self, item):
        ppu_bounds = item["ppuBounds"]
        bounds = self.window.contentView().bounds()
        scale_x = bounds.size.width / 256.0
        scale_y = bounds.size.height / 240.0
        x = ppu_bounds["x"] * scale_x
        y = bounds.size.height - (
            ppu_bounds["y"] + ppu_bounds["height"]
        ) * scale_y
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(
            x, y, max(ppu_bounds["width"] * scale_x, 24.0),
            max(ppu_bounds["height"] * scale_y, 12.0),
        ))
        field.setEditable_(False)
        field.setSelectable_(False)
        field.setBezeled_(False)
        field.setDrawsBackground_(False)
        field.setTextColor_(NSColor.systemGreenColor())
        field.setFont_(NSFont.monospacedSystemFontOfSize_weight_(
            max(7.0, 3.5 * scale_y), 0.0
        ))
        field.setWantsLayer_(True)
        field.layer().setBorderWidth_(2.0)
        field.layer().setBorderColor_(NSColor.systemGreenColor().CGColor())
        ratio = float(item.get("visibleRatio", 1.0))
        field.setStringValue_(
            f"{item.get('recordId', '?')} [{item.get('kind', '?')}] "
            f"{ratio:.0%}"
        )
        self.window.contentView().addSubview_(field)
        self.drawFields.append(field)

    @python_method
    def _render(self):
        for field in self.drawFields:
            field.removeFromSuperview()
        self.drawFields = []
        command = self.latestCommand
        if not command.get("visible"):
            return
        for item in command.get("items", []):
            self._field(item["text"], item["ppuBounds"], item["fontSize"])
        if DEBUG_REGIONS:
            for item in command.get("items", []):
                self._debug_region(item)
        self.window.orderFrontRegardless()

    def finish_(self, value):
        del value
        NSApp.terminate_(None)


def main() -> None:
    global DEBUG_REGIONS
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug-regions", action="store_true")
    args = parser.parse_args()
    DEBUG_REGIONS = args.debug_regions
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = SubtitleController.alloc().init()
    app.setDelegate_(controller)
    app.run()


if __name__ == "__main__":
    main()
