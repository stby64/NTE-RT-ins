# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
import shutil
import ctypes
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, DISABLED, END, LEFT, NORMAL, RIGHT, Button, Checkbutton, Frame, Label, StringVar, Tk, filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


APP_NAME = "NTE RT 한국어 안전 설치기"
APP_VERSION = "0.3.1"
APP_DIR = Path(__file__).resolve().parent
DEFAULT_GAME_DIR = Path(r"C:\Program Files\Neverness To Everness")
BACKUP_DIR_NAME = "_nte_rt_kr_backups"
PROXY_DLLS = ("winmm.dll", "dxgi.dll")
MANAGED_FILES = (*PROXY_DLLS, "OptiScaler.ini", "OptiScaler.log")
MANAGED_DIRS = ("OptiScaler",)
KNOWN_GAME_EXES = ("HTGame.exe", "NTEGlobalGame.exe")

PROFILES = {
    "RTX 5090 추천": {
        "SpoofedGPUName": "NVIDIA GeForce RTX 5090",
        "SpoofedDeviceId": "0x2B85",
        "DxgiVRAM": "32",
    },
    "RTX 4090 대체": {
        "SpoofedGPUName": "NVIDIA GeForce RTX 4090",
        "SpoofedDeviceId": "0x2684",
        "DxgiVRAM": "16",
    },
    "RTX 5080M 실험": {
        "SpoofedGPUName": "NVIDIA GeForce RTX 5080 Laptop GPU",
        "SpoofedDeviceId": "0x2C59",
        "DxgiVRAM": "16",
    },
}


class AppError(Exception):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def now_id() -> str:
    stamp = datetime.now()
    return stamp.strftime("%Y%m%d-%H%M%S") + f"-{stamp.microsecond // 1000:03d}"


def safe_under(path: Path, base: Path) -> Path:
    resolved = path.resolve()
    root = base.resolve()
    if resolved != root and root not in resolved.parents:
        raise AppError(f"허용되지 않은 경로입니다: {resolved}")
    return resolved


def is_likely_game_exe(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() != ".exe":
        return False
    name = path.name.lower()
    if name in {exe.lower() for exe in KNOWN_GAME_EXES}:
        return True
    parent = str(path.parent).lower()
    return "win64" in parent and any(token in name for token in ("ht", "nte", "neverness", "ananta"))


def likely_exe_candidates(base: Path) -> list[Path]:
    candidates: list[Path] = []
    for exe in KNOWN_GAME_EXES:
        candidates.extend(
            [
                base / exe,
                base / "Client" / "WindowsNoEditor" / "HT" / "Binaries" / "Win64" / exe,
                base / "WindowsNoEditor" / "HT" / "Binaries" / "Win64" / exe,
                base / "HT" / "Binaries" / "Win64" / exe,
                base / "Binaries" / "Win64" / exe,
            ]
        )
    win64_dirs = [
        base,
        base / "Client" / "WindowsNoEditor" / "HT" / "Binaries" / "Win64",
        base / "WindowsNoEditor" / "HT" / "Binaries" / "Win64",
        base / "HT" / "Binaries" / "Win64",
        base / "Binaries" / "Win64",
    ]
    for folder in win64_dirs:
        if folder.is_dir():
            candidates.extend(folder.glob("*.exe"))
    seen = set()
    unique = []
    for item in candidates:
        key = str(item).lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def find_game_exe(path: Path) -> Path:
    if is_likely_game_exe(path):
        return path
    for candidate in likely_exe_candidates(path):
        if is_likely_game_exe(candidate):
            return candidate
    if path.is_dir():
        skipped = {"$RECYCLE.BIN", "System Volume Information", "Saved", "Logs", "UserData", "cef_cache_0"}
        checked = 0
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in skipped and not d.startswith(".")]
            folder = Path(root)
            for file_name in files:
                candidate = folder / file_name
                if is_likely_game_exe(candidate):
                    return candidate
            checked += len(files)
            if checked > 250000:
                break
    raise AppError("게임 실행파일을 찾지 못했습니다. Win64 폴더 안의 HTGame.exe 또는 실제 NTE 실행파일을 직접 선택해 주세요.")


def find_optiscaler_payload(path: Path) -> tuple[Path, Path]:
    if not path.is_dir():
        raise AppError("OptiScaler 압축을 풀어둔 폴더를 선택해야 합니다.")
    dll = next(path.rglob("OptiScaler.dll"), None)
    ini = next(path.rglob("OptiScaler.ini"), None)
    if not dll or not ini:
        raise AppError("선택한 폴더 안에서 OptiScaler.dll / OptiScaler.ini를 찾지 못했습니다.")
    return dll, ini


def contains_marker(path: Path, marker: bytes) -> bool:
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            if marker in chunk:
                return True
    return False


def looks_like_optiscaler_proxy(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 1_000_000 and contains_marker(path, b"OptiScaler")
    except OSError:
        return False


def item_fingerprint(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    if path.is_dir():
        digest = hashlib.sha256()
        count = 0
        for file in sorted((p for p in path.rglob("*") if p.is_file()), key=lambda p: str(p.relative_to(path)).lower()):
            digest.update(str(file.relative_to(path)).lower().encode("utf-8"))
            digest.update(b"\0")
            digest.update(sha256(file).encode("ascii"))
            count += 1
        return {"exists": True, "kind": "dir", "fileCount": count, "sha256": digest.hexdigest().upper()}
    return {"exists": True, "kind": "file", "size": path.stat().st_size, "sha256": sha256(path)}


def backup_item(win64: Path, rel: str, backup_dir: Path) -> dict:
    source = safe_under(win64 / rel, win64)
    record = {"rel": rel, "existed": source.exists(), "before": item_fingerprint(source)}
    if source.exists():
        destination = backup_dir / "files" / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        record["backupRel"] = str(Path("files") / rel)
    return record


def build_config(template_ini: Path, target_exe: str, profile_name: str) -> str:
    profile = PROFILES[profile_name]
    values = {
        "FGInput": "nofg",
        "FGOutput": "nofg",
        "FTInput": "false",
        "SpoofedVendorId": "0x10de",
        "SpoofedDeviceId": profile["SpoofedDeviceId"],
        "TargetVendorId": "0x10de",
        "TargetDeviceId": "auto",
        "SpoofedGPUName": profile["SpoofedGPUName"],
        "OptiDllPath": r".\OptiScaler",
        "StreamlineSpoofing": "true",
        "Dxgi": "true",
        "DxgiFactoryWrapping": "false",
        "DxgiVRAM": profile["DxgiVRAM"],
        "Registry": "false",
        "User32": "false",
        "UseFakenvapi": "false",
        "TargetProcessName": target_exe,
        "LogToFile": "true",
        "LogLevel": "0",
        "SingleFile": "true",
        "CheckForUpdate": "false",
    }
    lines = template_ini.read_text(encoding="utf-8", errors="replace").splitlines()
    for key, value in values.items():
        lines = set_ini_value(lines, key, value)
    lines = set_ini_section_value(lines, "Hooks", "HookOriginalNvngxOnly", "true")
    return "\n".join(lines).rstrip() + "\n"


def set_ini_value(lines: list[str], key: str, value: str) -> list[str]:
    prefix = key.lower()
    changed = False
    out = []
    for line in lines:
        left = line.split("=", 1)[0].strip().lower() if "=" in line else ""
        if not changed and left == prefix:
            out.append(f"{key}={value}")
            changed = True
        else:
            out.append(line)
    if not changed:
        out.append(f"{key}={value}")
    return out


def set_ini_section_value(lines: list[str], section: str, key: str, value: str) -> list[str]:
    section_header = f"[{section}]".lower()
    key_lower = key.lower()
    out = []
    in_section = False
    changed = False
    inserted = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_section and not changed and not inserted:
                out.append(f"{key}={value}")
                inserted = True
            in_section = stripped.lower() == section_header
        if in_section and "=" in line and line.split("=", 1)[0].strip().lower() == key_lower:
            if not changed:
                out.append(f"{key}={value}")
                changed = True
            continue
        out.append(line)
    if not changed and not inserted:
        if out and out[-1].strip():
            out.append("")
        out.append(f"[{section}]")
        out.append(f"{key}={value}")
    return out


def install(win64: Path, opt_folder: Path, profile_name: str, proxy_dll: str, allow_existing_proxy: bool) -> Path:
    if proxy_dll not in PROXY_DLLS:
        raise AppError("Unsupported proxy DLL")
    exe_candidates = [p for p in win64.glob("*.exe") if is_likely_game_exe(p)]
    if not exe_candidates:
        raise AppError("선택한 경로가 게임 Win64 폴더가 아닙니다. 실행파일이 있는 폴더를 다시 선택해 주세요.")
    game_exe = exe_candidates[0].name
    dll, template_ini = find_optiscaler_payload(opt_folder)
    existing_proxy = win64 / proxy_dll
    if existing_proxy.exists() and not looks_like_optiscaler_proxy(existing_proxy) and not allow_existing_proxy:
        raise AppError(f"기존 {proxy_dll}이 OptiScaler로 보이지 않습니다. 다른 모드 파일일 수 있어 자동 교체를 멈췄습니다.")

    if not has_write_access(win64):
        raise AppError(
            "게임 폴더에 쓸 권한이 없습니다.\n\n"
            "게임이 Program Files 아래에 설치되어 있으면 관리자 권한으로 실행해야 합니다.\n"
            "이 창을 닫고 run_as_admin.bat을 실행해 주세요."
        )

    backup_dir = win64 / BACKUP_DIR_NAME / now_id()
    backup_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "created": datetime.now().isoformat(timespec="seconds"),
        "win64": str(win64),
        "gameExe": game_exe,
        "profile": profile_name,
        "proxyDll": proxy_dll,
        "managedFiles": list(MANAGED_FILES),
        "managedDirs": list(MANAGED_DIRS),
        "items": [],
    }
    for rel in MANAGED_FILES + MANAGED_DIRS:
        manifest["items"].append(backup_item(win64, rel, backup_dir))

    for other_proxy in PROXY_DLLS:
        other_path = win64 / other_proxy
        if other_proxy != proxy_dll and looks_like_optiscaler_proxy(other_path):
            other_path.unlink()
    shutil.copy2(dll, win64 / proxy_dll)
    opt_dir = win64 / "OptiScaler"
    if opt_dir.exists():
        shutil.rmtree(opt_dir)
    opt_dir.mkdir(parents=True)
    release_root = dll.parent
    for item in release_root.iterdir():
        if item.name in {"OptiScaler.dll", "OptiScaler.ini", "Licenses"}:
            continue
        if item.is_file() and item.suffix.lower() in {".dll", ".ini"}:
            shutil.copy2(item, opt_dir / item.name)
        elif item.is_dir() and item.name == "D3D12_Optiscaler":
            shutil.copytree(item, opt_dir / item.name)
    shutil.copy2(template_ini, opt_dir / "_source_OptiScaler.ini")
    (win64 / "OptiScaler.ini").write_text(build_config(template_ini, game_exe, profile_name), encoding="ascii", errors="ignore")
    (win64 / "OptiScaler.log").write_text("", encoding="utf-8")
    for record in manifest["items"]:
        record["after"] = item_fingerprint(win64 / record["rel"])
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return backup_dir


def has_write_access(folder: Path) -> bool:
    probe = folder / f".nte_rt_write_test_{os.getpid()}.tmp"
    try:
        probe.write_text("test", encoding="ascii")
        probe.unlink()
        return True
    except OSError:
        return False


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def list_backups(win64: Path) -> list[Path]:
    root = win64 / BACKUP_DIR_NAME
    if not root.is_dir():
        return []
    return sorted((p for p in root.iterdir() if (p / "manifest.json").is_file()), reverse=True)


def restore(win64: Path, backup_dir: Path) -> list[str]:
    backup_dir = safe_under(backup_dir, win64 / BACKUP_DIR_NAME)
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    operations = []
    for record in manifest.get("items", []):
        rel = record.get("rel")
        if rel not in MANAGED_FILES + MANAGED_DIRS:
            continue
        target = safe_under(win64 / rel, win64)
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        if record.get("existed") and record.get("backupRel"):
            source = safe_under(backup_dir / record["backupRel"], backup_dir)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            operations.append(f"복원: {rel}")
        else:
            operations.append(f"삭제: {rel}")
    return operations


class Gui:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("900x640")
        self.game_path = StringVar(value=str(DEFAULT_GAME_DIR) if DEFAULT_GAME_DIR.exists() else "")
        self.win64_path = StringVar()
        self.opt_path = StringVar(value=str(APP_DIR / "OptiScaler") if (APP_DIR / "OptiScaler").is_dir() else "")
        self.profile = StringVar(value="RTX 5090 추천")
        self.proxy_dll = StringVar(value="dxgi.dll")
        self.allow_existing_proxy = StringVar(value="0")
        self._build()

    def _build(self) -> None:
        Label(self.root, text="NTE 레이트레이싱 언락 설치/원복", font=("Malgun Gothic", 16, "bold")).pack(pady=(14, 6))
        Label(self.root, text="자동 다운로드 없음. 선택한 OptiScaler 폴더와 게임 Win64 폴더에만 작업합니다.").pack()
        self._row("NTE 폴더 또는 실행파일", self.game_path, self.pick_game_folder, self.pick_game_exe, self.detect_game)
        self._row("OptiScaler 압축 해제 폴더", self.opt_path, self.pick_opt_folder, None, None)
        row = Frame(self.root)
        row.pack(fill="x", padx=18, pady=6)
        Label(row, text="GPU 프로필", width=22, anchor="w").pack(side=LEFT)
        ttk.Combobox(row, textvariable=self.profile, values=list(PROFILES), state="readonly", width=28).pack(side=LEFT)
        Label(row, text="프록시", padx=12).pack(side=LEFT)
        ttk.Combobox(row, textvariable=self.proxy_dll, values=list(PROXY_DLLS), state="readonly", width=10).pack(side=LEFT)
        Checkbutton(row, text="기존 프록시 DLL 교체 허용", variable=self.allow_existing_proxy, onvalue="1", offvalue="0").pack(side=LEFT, padx=16)
        actions = Frame(self.root)
        actions.pack(fill="x", padx=18, pady=8)
        Button(actions, text="상태 확인", command=self.inspect).pack(side=LEFT, padx=4)
        Button(actions, text="백업 후 설치", command=self.install_clicked).pack(side=LEFT, padx=4)
        Button(actions, text="최근 백업으로 원복", command=self.restore_clicked).pack(side=LEFT, padx=4)
        Button(actions, text="닫기", command=self.root.destroy).pack(side=RIGHT, padx=4)
        self.log = ScrolledText(self.root, height=23)
        self.log.pack(fill=BOTH, expand=True, padx=18, pady=(4, 16))
        if is_admin():
            self.say("관리자 권한: 예")
        else:
            self.say("관리자 권한: 아니오 - Program Files에 설치할 때는 run_as_admin.bat으로 다시 켜세요.")
        self.say("1. NTE 설치 폴더를 선택하고 Win64 찾기를 누르세요.")
        self.say("2. 못 찾으면 Win64 폴더 안의 실제 게임 .exe를 'EXE 선택'으로 직접 고르세요.")
        self.say("3. OptiScaler 공식 Release .7z를 직접 압축 해제한 폴더를 선택하세요.")
        self.say("4. 설치 후에는 이 프로그램을 매번 켤 필요가 없습니다.")

    def _row(self, label: str, var: StringVar, pick_folder_cmd, pick_file_cmd, detect_cmd) -> None:
        row = Frame(self.root)
        row.pack(fill="x", padx=18, pady=6)
        Label(row, text=label, width=22, anchor="w").pack(side=LEFT)
        ttk.Entry(row, textvariable=var).pack(side=LEFT, fill="x", expand=True)
        Button(row, text="폴더", command=pick_folder_cmd).pack(side=LEFT, padx=4)
        if pick_file_cmd:
            Button(row, text="EXE 선택", command=pick_file_cmd).pack(side=LEFT, padx=4)
        if detect_cmd:
            Button(row, text="Win64 찾기", command=detect_cmd).pack(side=LEFT, padx=4)

    def say(self, text: str) -> None:
        self.log.configure(state=NORMAL)
        self.log.insert(END, text + "\n")
        self.log.see(END)
        self.log.configure(state=DISABLED)

    def pick_game_folder(self) -> None:
        selected = filedialog.askdirectory(title="NTE 설치 폴더 또는 Win64 폴더 선택")
        if selected:
            self.game_path.set(selected)

    def pick_game_exe(self) -> None:
        selected = filedialog.askopenfilename(title="NTE 게임 실행파일 선택", filetypes=[("실행파일", "*.exe"), ("모든 파일", "*.*")])
        if selected:
            self.game_path.set(selected)
            self.detect_game()

    def pick_opt_folder(self) -> None:
        selected = filedialog.askdirectory(title="OptiScaler 압축 해제 폴더 선택")
        if selected:
            self.opt_path.set(selected)

    def detect_game(self) -> None:
        try:
            exe = find_game_exe(Path(self.game_path.get()))
            self.win64_path.set(str(exe.parent))
            self.say(f"게임 실행파일 확인: {exe}")
            self.say(f"작업 Win64 폴더: {exe.parent}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self.say(f"오류: {exc}")

    def current_win64(self) -> Path:
        if self.win64_path.get():
            return Path(self.win64_path.get())
        exe = find_game_exe(Path(self.game_path.get()))
        self.win64_path.set(str(exe.parent))
        return exe.parent

    def inspect(self) -> None:
        try:
            win64 = self.current_win64()
            dll, ini = find_optiscaler_payload(Path(self.opt_path.get()))
            self.say("----- 상태 확인 -----")
            self.say(f"Win64: {win64}")
            self.say(f"OptiScaler.dll: {dll}")
            self.say(f"OptiScaler.ini: {ini}")
            self.say("OptiScaler 준비 상태: 정상")
            self.say(f"이번 설치 프록시: {self.proxy_dll.get()}")
            self.say("게임 폴더 설치 상태:")
            for rel in MANAGED_FILES + MANAGED_DIRS:
                target = win64 / rel
                self.say(f"{rel}: {'있음' if target.exists() else '없음'}")
            backups = list_backups(win64)
            self.say(f"백업 개수: {len(backups)}")
            if backups:
                self.say(f"최근 백업: {backups[0].name}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self.say(f"오류: {exc}")

    def install_clicked(self) -> None:
        try:
            win64 = self.current_win64()
            msg = (
                "게임과 런처를 완전히 종료한 상태에서 진행하세요.\n\n"
                "변경 대상:\n"
                f"- {self.proxy_dll.get()}\n- OptiScaler.ini\n- OptiScaler.log\n- OptiScaler\\\n\n"
                "설치 전 백업을 만들고 진행합니다."
            )
            if not messagebox.askyesno(APP_NAME, msg):
                return
            backup_dir = install(
                win64,
                Path(self.opt_path.get()),
                self.profile.get(),
                self.proxy_dll.get(),
                self.allow_existing_proxy.get() == "1",
            )
            self.say(f"설치 완료. 백업 위치: {backup_dir}")
            messagebox.showinfo(APP_NAME, "설치가 끝났습니다. 게임에서 그래픽 프리셋을 극치/Ultra 이상으로 맞춘 뒤 옵션을 확인하세요.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self.say(f"오류: {exc}")

    def restore_clicked(self) -> None:
        try:
            win64 = self.current_win64()
            backups = list_backups(win64)
            if not backups:
                raise AppError("복원할 백업이 없습니다.")
            backup_dir = backups[0]
            if not messagebox.askyesno(APP_NAME, f"최근 백업으로 원복할까요?\n\n{backup_dir.name}"):
                return
            operations = restore(win64, backup_dir)
            self.say("원복 완료:")
            for op in operations:
                self.say(f"- {op}")
            messagebox.showinfo(APP_NAME, "원복이 끝났습니다.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self.say(f"오류: {exc}")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    Gui().run()
