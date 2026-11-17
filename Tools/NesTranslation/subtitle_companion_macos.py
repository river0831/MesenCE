"""Minimal AppKit subtitle window driven by JSON lines on stdin."""

from __future__ import annotations

import argparse
import json
import sys
import threading

try:
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGNullWindowID,
        kCGWindowBounds,
        kCGWindowLayer,
        kCGWindowListOptionOnScreenOnly,
        kCGWindowOwnerName,
    )
except ImportError:  # pragma: no cover - this companion is macOS-only.
    CGWindowListCopyWindowInfo = None

from AppKit import (
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSButton,
    NSButtonTypeSwitch,
    NSColor,
    NSControlStateValueOff,
    NSControlStateValueOn,
    NSFont,
    NSLineBreakByCharWrapping,
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
    DEBUG_LAYER_OPTIONS = (
        ("visual-region", "紫色：视觉大区域", True),
        ("character", "黄色：单个字符", False),
        ("text-line", "蓝色：同一行文本", False),
        ("block-candidate", "橙色：语义候选块", False),
        ("result-box", "红/绿色：翻译结果与来源", True),
    )

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
        self.pendingCommand = None
        self.commandScheduled = False
        self.commandLock = threading.Lock()
        self.mesenSizeSynchronized = False
        self.debugLayerEnabled = {
            key: enabled for key, _, enabled in self.DEBUG_LAYER_OPTIONS
        }
        self.debugLayerKeysByTag = {
            index: key
            for index, (key, _, _) in enumerate(self.DEBUG_LAYER_OPTIONS)
        }
        self.window.orderFrontRegardless()
        if DEBUG_REGIONS:
            self._create_debug_settings_window(screen, rect)
        threading.Thread(target=self._read_commands, daemon=True).start()

    @python_method
    def _synchronize_mesen_size(self):
        if self.mesenSizeSynchronized or CGWindowListCopyWindowInfo is None:
            return
        windows = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly, kCGNullWindowID
        ) or []
        candidates = []
        for item in windows:
            owner = str(item.get(kCGWindowOwnerName, ""))
            bounds = item.get(kCGWindowBounds, {})
            width = float(bounds.get("Width", 0))
            height = float(bounds.get("Height", 0))
            if (
                "mesen" in owner.lower()
                and int(item.get(kCGWindowLayer, 0)) == 0
                and width >= 256 and height >= 240
            ):
                candidates.append((width * height, width))
        if not candidates:
            return
        game_width = max(candidates)[1]
        screen = NSScreen.mainScreen().visibleFrame()
        target_width = min(
            game_width,
            screen.size.width,
            max(256.0, (screen.size.height - 48.0) * 256.0 / 240.0),
        )
        # Mesen's NES viewport preserves 256:240 below its title/menu chrome.
        # Matching that viewport width and aspect ratio makes every PPU box
        # land at the same pixel scale in both windows.
        self.window.setContentSize_(NSMakeSize(
            target_width, target_width * 240.0 / 256.0
        ))
        self.mesenSizeSynchronized = True

    @python_method
    def _create_debug_settings_window(self, screen, mirror_rect):
        width, height = 250, 190
        x = min(
            mirror_rect.origin.x + mirror_rect.size.width + 12,
            screen.origin.x + screen.size.width - width,
        )
        y = min(
            mirror_rect.origin.y + mirror_rect.size.height - height,
            screen.origin.y + screen.size.height - height,
        )
        self.debugWindow = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height),
            NSWindowStyleMaskTitled,
            NSBackingStoreBuffered,
            False,
        )
        self.debugWindow.setTitle_("调试显示")
        self.debugWindow.setLevel_(4)
        self.debugButtons = []
        for index, (key, title, enabled) in enumerate(self.DEBUG_LAYER_OPTIONS):
            button = NSButton.alloc().initWithFrame_(NSMakeRect(
                16, height - 38 - index * 30, width - 32, 24
            ))
            button.setButtonType_(NSButtonTypeSwitch)
            button.setTitle_(title)
            button.setTag_(index)
            button.setState_(
                NSControlStateValueOn if enabled else NSControlStateValueOff
            )
            button.setTarget_(self)
            button.setAction_("toggleDebugLayer:")
            self.debugWindow.contentView().addSubview_(button)
            self.debugButtons.append(button)
        self.debugWindow.orderFrontRegardless()

    def toggleDebugLayer_(self, sender):  # noqa: N802
        key = self.debugLayerKeysByTag.get(int(sender.tag()))
        if key is None:
            return
        self.debugLayerEnabled[key] = (
            int(sender.state()) == int(NSControlStateValueOn)
        )
        self._render()

    @python_method
    def _read_commands(self):
        for line in sys.stdin:
            try:
                command = json.loads(line)
            except (ValueError, TypeError):
                continue
            # The emulator can publish faster than AppKit can rebuild the
            # debug view. Keep only the newest not-yet-rendered snapshot so
            # the UI never replays a growing queue of obsolete game states.
            with self.commandLock:
                self.pendingCommand = command
                should_schedule = not self.commandScheduled
                if should_schedule:
                    self.commandScheduled = True
            if should_schedule:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "applyPendingState:", None, False
                )
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "finish:", None, False
        )

    def applyPendingState_(self, value):  # noqa: N802
        del value
        with self.commandLock:
            command = self.pendingCommand
            self.pendingCommand = None
            self.commandScheduled = False
        if command is None or command == self.latestCommand:
            return
        self._synchronize_mesen_size()
        self.latestCommand = command
        self._render()

    def windowDidResize_(self, notification):  # noqa: N802
        del notification
        self._render()

    @python_method
    def _field(self, text, ppu_bounds, font_size):
        bounds = self.window.contentView().bounds()
        scale_x = bounds.size.width / 256.0
        scale_y = bounds.size.height / 240.0
        # Source coordinates are authoritative. Expanding a field around its
        # centre makes long translations drift, and a field near the right
        # edge can then extend beyond both its debug box and the viewport.
        # Keep the exact source rectangle and wrap inside it instead.
        x = ppu_bounds["x"] * scale_x
        y = bounds.size.height - (
            ppu_bounds["y"] + ppu_bounds["height"]
        ) * scale_y
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(
            x, y, ppu_bounds["width"] * scale_x,
            ppu_bounds["height"] * scale_y,
        ))
        field.setEditable_(False)
        field.setSelectable_(False)
        field.setBezeled_(False)
        field.setDrawsBackground_(True)
        field.setBackgroundColor_(NSColor.blackColor())
        field.setTextColor_(NSColor.whiteColor())
        field.setFont_(NSFont.systemFontOfSize_(font_size * scale_y))
        field.setAlignment_(0)
        field.setMaximumNumberOfLines_(0)
        field.cell().setWraps_(True)
        field.cell().setLineBreakMode_(NSLineBreakByCharWrapping)
        field.setStringValue_(text)
        self.window.contentView().addSubview_(field)
        self.drawFields.append(field)

    @python_method
    def _debug_region(self, item):
        ppu_bounds = item["ppuBounds"]
        fallback = item.get("kind") in ("content", "vocabulary", "dynamic")
        debug_color = (
            NSColor.systemRedColor() if fallback
            else NSColor.systemGreenColor()
        )
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
        field.setTextColor_(debug_color)
        field.setFont_(NSFont.monospacedSystemFontOfSize_weight_(
            max(7.0, 3.5 * scale_y), 0.0
        ))
        field.setWantsLayer_(True)
        field.layer().setBorderWidth_(2.0)
        field.layer().setBorderColor_(debug_color.CGColor())
        ratio = float(item.get("visibleRatio", 1.0))
        field.setStringValue_(
            f"{item.get('recordId', '?')} [{item.get('kind', '?')}] "
            f"{'fallback' if fallback else 'source'} {ratio:.0%}"
        )
        self.window.contentView().addSubview_(field)
        self.drawFields.append(field)

    @python_method
    def _nametable_debug_region(self, item):
        ppu_bounds = item["ppuBounds"]
        debug_type = item.get("debugType")
        debug_color = {
            "visual-region": NSColor.systemPurpleColor(),
            "character": NSColor.systemYellowColor(),
            "text-line": NSColor.systemBlueColor(),
            "block-candidate": NSColor.systemOrangeColor(),
        }.get(debug_type, NSColor.systemGrayColor())
        bounds = self.window.contentView().bounds()
        scale_x = bounds.size.width / 256.0
        scale_y = bounds.size.height / 240.0
        x = ppu_bounds["x"] * scale_x
        y = bounds.size.height - (
            ppu_bounds["y"] + ppu_bounds["height"]
        ) * scale_y
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(
            x, y, max(ppu_bounds["width"] * scale_x, 18.0),
            max(ppu_bounds["height"] * scale_y, 10.0),
        ))
        field.setEditable_(False)
        field.setSelectable_(False)
        field.setBezeled_(False)
        field.setDrawsBackground_(False)
        field.setTextColor_(debug_color)
        font_size = 2.8 if debug_type == "character" else 3.5
        field.setFont_(NSFont.monospacedSystemFontOfSize_weight_(
            max(6.0, font_size * scale_y), 0.0
        ))
        field.setWantsLayer_(True)
        field.layer().setBorderWidth_(
            0.75 if debug_type == "character" else (
                2.0 if debug_type == "visual-region" else 1.5
            )
        )
        field.layer().setBorderColor_(debug_color.CGColor())
        field.setStringValue_(str(item.get("label", debug_type or "?")))
        self.window.contentView().addSubview_(field)
        self.drawFields.append(field)

    @python_method
    def _render(self):
        for field in self.drawFields:
            field.removeFromSuperview()
        self.drawFields = []
        command = self.latestCommand
        if not command.get("visible") and not (
            DEBUG_REGIONS and command.get("debugRegions")
        ):
            return
        for item in command.get("items", []):
            self._field(item["text"], item["ppuBounds"], item["fontSize"])
        if DEBUG_REGIONS:
            for item in command.get("debugRegions", []):
                if self.debugLayerEnabled.get(item.get("debugType"), False):
                    self._nametable_debug_region(item)
            if self.debugLayerEnabled.get("result-box", False):
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
