# SahneBul Video İndir — Android MVP

Sadece video indirme özelliğini içeren ilk Android sürümü. Kivy + yt-dlp
(Python kütüphanesi) kullanır.

## Önemli sınırlama

ffmpeg Android tarafına henüz eklenmedi. Bu yüzden yalnızca hem görüntü
hem sesin **tek dosyada** geldiği formatlar listelenir. YouTube gibi
sitelerde yüksek çözünürlükler genelde ayrı akış halinde gelir ve
birleştirmek için ffmpeg gerekir — bazı videolarda listede sadece
360p/480p gibi düşük kaliteler görünebilir. Sonraki adımda FFmpegKit
eklenerek bu çözülebilir.

## Derleme (Buildozer ile)

Buildozer Windows'ta çalışmaz — **WSL (Ubuntu) ya da bir Linux makine**
gerekir.

### 1) WSL kurulumu (Windows'tan)

PowerShell'i yönetici olarak aç:

```
wsl --install
```

Bilgisayarı yeniden başlat, Ubuntu kullanıcı adı/şifresi oluştur.

### 2) WSL (Ubuntu) içinde gerekli paketler

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip openjdk-17-jdk \
    autoconf libtool pkg-config zlib1g-dev libncurses5-dev cmake libffi-dev \
    libssl-dev build-essential

pip install --user buildozer cython==0.29.36
```

### 3) Proje dosyalarını WSL'e kopyala

Windows'taki bu klasörü (`SahneBulAndroid`) WSL içine kopyala, örneğin:

```bash
cp -r /mnt/c/Users/aileo/Downloads/SahneBulAndroid ~/sahnebul-android
cd ~/sahnebul-android
```

### 4) İlk derleme

```bash
~/.local/bin/buildozer -v android debug
```

İlk derleme Android SDK/NDK'yı otomatik indirir — **uzun sürer (30-60 dk)**
ve internet gerektirir. Bitince APK şurada olur:

```
bin/sahnebulindir-0.1-arm64-v8a_armeabi-v7a-debug.apk
```

### 5) Telefona kurmak

Telefonu USB ile bağla, USB hata ayıklamayı aç, sonra:

```bash
~/.local/bin/buildozer android deploy run
```

ya da APK dosyasını telefona kopyalayıp elle kur (telefon "bilinmeyen
kaynaklardan kurulum"a izin vermeli).

## Sonraki adımlar (bu MVP'den sonra)

- ffmpeg/FFmpegKit ekleyerek yüksek çözünürlüklerde ses+görüntü birleştirme
- İndirilen dosyayı sistem "İndirilenler" klasörüne (MediaStore API ile)
  kaydetme, böylece dosya yöneticisinde/galeri'de görünür olur
- Oynatma listesi desteği
- Uygulama ikonu, splash screen
- Premium/lisans sistemi (muhtemelen Google Play Billing ile)
