# -*- coding: utf-8 -*-
# Created for Pisi 3.12 Project by Ergün
# Focus: KDE 6 & Plasma 6 Transition, Qt 6 Integration, x86_64 lib64 Optimization

from pathlib import Path
from pisi.actionsapi import get, cmaketools, shelltools
import pisi.context as ctx

class KDE6Config:
    """KDE 6 ve Qt 6 spesifik sistem hiyerarşisini yönetir."""
    # PMP: Bellek verimliliği için __slots__ (RefactorPlan uyumu)
    __slots__ = ("prefix", "bin", "lib", "libexec", "share", "sysconf", "qml", "plugins", "mkspecs")

    def __init__(self):
        # PMP: Modern x86_64 Linux hiyerarşisi
        self.prefix = Path(f"/{get.defaultprefixDIR()}")
        self.bin = self.prefix / "bin"
        self.lib = self.prefix / "lib64"  # x86_64 standart kütüphane yolu
        self.libexec = self.lib / "libexec"
        self.share = self.prefix / "share"
        self.sysconf = Path("/etc")
        
        # PMP: Qt 6 tabanlı yeni nesil KDE yolları
        qt6_base = self.lib / "qt6"
        self.qml = qt6_base / "qml"
        self.plugins = qt6_base / "plugins"
        self.mkspecs = qt6_base / "mkspecs/modules"

# Global Yapılandırma Nesnesi
kde6 = KDE6Config()

def configure(parameters: str = '', install_prefix: str = None, source_dir: str = '..'):
    """
    PMP: CMake kullanarak KDE 6 projesini yapılandırır.
    KDE 6 (Extra CMake Modules) standartlarını ve Qt 6 yollarını enjekte eder.
    """
    prefix = install_prefix or str(kde6.prefix)
    
    # Derleme dizini yönetimi
    shelltools.makedirs("build")
    shelltools.cd("build")

    # PMP: KDE 6 için optimize edilmiş modern CMake parametreleri
    # RefactorPlan: f-string kullanımı ve net isimlendirme
    cmake_params = (
        f"-DCMAKE_BUILD_TYPE=Release "
        f"-DCMAKE_INSTALL_PREFIX={prefix} "
        f"-DCMAKE_INSTALL_LIBDIR=lib64 "
        f"-DKDE_INSTALL_LIBEXECDIR={kde6.libexec} "
        f"-DKDE_INSTALL_USE_QT_SYS_PATHS=ON "
        f"-DKDE_INSTALL_QMLDIR={kde6.qml} "
        f"-DKDE_INSTALL_PLUGINDIR={kde6.plugins} "
        f"-DKDE_INSTALL_SYSCONFDIR={kde6.sysconf} "
        f"-DECM_MKSPECS_INSTALL_DIR={kde6.mkspecs} "
        f"-DBUILD_TESTING=OFF "
        f"-Wno-dev "
        f"{parameters}"
    ).strip()

    ctx.ui.info(f"[*] KDE 6 Yapılandırması başlatılıyor: {cmake_params}")
    cmaketools.configure(cmake_params, prefix, source_dir)
    shelltools.cd("..")

def make(parameters: str = ''):
    """PMP: Build dizini içinde x86_64 JOBS uyumlu inşa sürecini başlatır."""
    cmaketools.make(f"-C build {parameters}")

def install(parameters: str = '', argument: str = 'install'):
    """PMP: Derlenen KDE 6 bileşenlerini PiSi paketleme dizinine yerleştirir."""
    cmaketools.install(f"-C build {parameters}", argument)
