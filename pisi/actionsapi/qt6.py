# -*- coding: utf-8 -*-
# Created for Pisi 3.12 Project by Ergün
# Focus: Qt 6 Build Automation, x86_64 Optimization, Modern Pathlib Integration

from pathlib import Path
from glob import glob
import pisi.context as ctx
import pisi.actionsapi
from pisi.actionsapi import get, cmaketools, shelltools

# PMP: Qt 6 Hiyerarşik Dizin Yapısı (RefactorPlan: Clear variable names)
class Qt6Config:
    """Qt 6 spesifik sistem yollarını ve araçlarını yönetir."""
    __slots__ = ("prefix", "bin", "lib", "include", "datadir", "docdir", "qmake", "plugins")

    def __init__(self):
        # PMP: Modern x86_64 Linux hiyerarşisi
        self.prefix = Path(f"/{get.defaultprefixDIR()}")
        self.bin = self.prefix / "bin"
        self.lib = self.prefix / "lib64"  # x86_64 standart kütüphane yolu
        self.include = self.prefix / "include/qt6"
        self.datadir = self.prefix / "share/qt6"
        self.docdir = Path(f"/{get.docDIR()}/qt6")
        
        # PMP: Qt 6 qmake aracı (Genellikle qmake6 adıyla gelir)
        self.qmake = self.bin / "qmake6"
        self.plugins = self.lib / "qt6/plugins"

# Global Config Instance
qt6 = Qt6Config()

class Qt6Error(pisi.actionsapi.Error):
    """PMP: Qt 6 inşa süreçleri için modernize edilmiş hata sınıfı."""
    def __init__(self, msg: str = ''):
        super().__init__(msg)
        ctx.ui.error(f"Qt 6 Hatası: {msg}")

def configure(project_file: str = '', parameters: str = '', install_prefix: str = None):
    """
    PMP: qmake6 ile Qt 6 projesini yapılandırır.
    x86_64 optimizasyon bayraklarını otomatik enjekte eder.
    """
    prefix = install_prefix or str(qt6.prefix)
    p_file = Path(project_file) if project_file else None

    # Proje dosyası kontrolü
    if p_file and not p_file.exists():
        raise Qt6Error(f"Proje dosyası bulunamadı: {project_file}")

    profiles = glob("*.pro")
    if not p_file and len(profiles) > 1:
        raise Qt6Error(f"Birden fazla .pro dosyası bulundu, birini seçmelisiniz: {', '.join(profiles)}")

    target = str(p_file) if p_file else ""
    
    # PMP: Qt 6 modern derleme bayrakları enjeksiyonu
    cmd = (f"{qt6.qmake} -makefile {target} PREFIX='{prefix}' "
           f"QMAKE_CFLAGS+='{get.CFLAGS()}' QMAKE_CXXFLAGS+='{get.CXXFLAGS()}' "
           f"QMAKE_LDFLAGS+='{get.LDFLAGS()}' "
           f"{parameters}").strip()

    ctx.ui.info(f"[*] Qt 6 Yapılandırması başlatılıyor: {cmd}")
    
    if shelltools.system(cmd):
        raise Qt6Error(f"Yapılandırma başarısız: {cmd}")

def make(parameters: str = ''):
    """PMP: Paralel make işlemini tetikler (x86_64 JOBS uyumlu)."""
    cmaketools.make(parameters)

def install(parameters: str = '', argument: str = 'install'):
    """INSTALL_ROOT kullanarak PiSi paketleme dizinine kurulum yapar."""
    install_cmd = f'INSTALL_ROOT="{get.installDIR()}" {parameters}'
    cmaketools.install(install_cmd, argument)

def cmake_configure(parameters: str = ''):
    """
    PMP: Qt 6 projeleri artık çoğunlukla CMake kullanır.
    Bu fonksiyon Qt 6 bileşenlerini CMake'e doğru şekilde tanıtır.
    """
    qt6_params = (f"-DQt6_DIR={qt6.lib}/cmake/Qt6 "
                  f"-DQT_QMAKE_EXECUTABLE={qt6.qmake} "
                  f"{parameters}")
    cmaketools.configure(qt6_params)
