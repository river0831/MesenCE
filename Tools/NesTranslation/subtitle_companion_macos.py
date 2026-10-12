"""Minimal AppKit subtitle window driven by JSON lines on stdin."""

from __future__ import annotations

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
    NSScreen,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject


class SubtitleController(NSObject):
    def applicationDidFinishLaunching_(self, notification):  # noqa: N802
        del notification
        screen = NSScreen.mainScreen().visibleFrame()
        width, height = 760, 300
        rect = NSMakeRect(
            screen.origin.x + (screen.size.width - width) / 2,
            screen.origin.y + 24,
            width,
            height,
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("NES Translation Subtitles")
        self.window.setLevel_(3)
        self.window.setBackgroundColor_(NSColor.blackColor())
        self.label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, 12, width - 40, 92)
        )
        self.label.setEditable_(False)
        self.label.setSelectable_(False)
        self.label.setBezeled_(False)
        self.label.setDrawsBackground_(False)
        self.label.setTextColor_(NSColor.whiteColor())
        self.label.setFont_(NSFont.systemFontOfSize_(25))
        self.label.setAlignment_(1)
        self.label.setMaximumNumberOfLines_(3)
        self.label.setStringValue_("等待游戏对话…")
        self.window.contentView().addSubview_(self.label)
        self.layoutLabels = []
        self.window.orderFrontRegardless()
        threading.Thread(target=self._read_commands, daemon=True).start()

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
        command = json.loads(payload)
        for label in self.layoutLabels:
            label.removeFromSuperview()
        self.layoutLabels = []
        if not command.get("visible"):
            self.label.setStringValue_("")
            return
        self.label.setStringValue_("\n".join(command.get("subtitles", [])))
        bounds = self.window.contentView().bounds()
        for item in command.get("labels", []):
            field = NSTextField.alloc().initWithFrame_(NSMakeRect(
                item["x"] * bounds.size.width,
                (1.0 - item["y"]) * bounds.size.height - 24,
                120,
                30,
            ))
            field.setEditable_(False)
            field.setBezeled_(False)
            field.setDrawsBackground_(False)
            field.setTextColor_(NSColor.whiteColor())
            field.setFont_(NSFont.systemFontOfSize_(22))
            field.setStringValue_(item["text"])
            self.window.contentView().addSubview_(field)
            self.layoutLabels.append(field)
        self.window.orderFrontRegardless()

    def finish_(self, value):
        del value
        NSApp.terminate_(None)


def main() -> None:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = SubtitleController.alloc().init()
    app.setDelegate_(controller)
    app.run()


if __name__ == "__main__":
    main()
