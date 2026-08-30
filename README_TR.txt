BALDI ANIM STUDIO v8
====================

V8 TIMELINE NAVIGASYON + ANIM8OR DUDAK PARSERİ
-----------------------------------------------
- Timeline artık animasyon süresinden bağımsız zoom/pan görünümüne sahiptir. Süreyi 1..100000 frame arası ayarlayabilirsin.
- “Süre / Son Frame” alanı gerçek animasyon sonunu belirler; son keyframe’den daha kısa bir değer girersen key kaybetmemek için otomatik korunur.
- −1s / +1s ile süreyi aktif FPS kadar hızlı kısaltıp uzatabilirsin.
- Alt + sol sürük veya orta tuş sürük = timeline yatay pan.
- Shift + mouse wheel = cursor çevresinde timeline zoom.
- Mouse’un yatay wheel hareketi = timeline pan.
- Alttaki Pan slider’ı ile zaman çizgisini serbestçe ileri/geri taşıyabilirsin. ◀◀ / ▶▶ bir ekran kaydırır, |◀ / ▶| başa/sona gider, Fit bütün süreyi sığdırır.
- PageUp / PageDown timeline görünümünü yaklaşık bir ekran ileri/geri kaydırır.
- Zoom seviyesi 2–80 px/frame arasında ayarlanır; uzun animasyonlarda keyframe’ler artık dar bir bölgeye sıkışmaz.
- Baldi dudağındaki üçgensi çıkıntının ana nedeni kaynak model değil parserdı: Anim8or Subdivision yüzeyleri kontrol kafesi gibi çiziliyor ve n-gon yüzler fan triangulation ile yanlış üçgenleniyordu.
- Mouth1/Mouth2 için Anim8or’un kayıtlı Working subdivision seviyeleri Catmull-Clark ile uygulanıyor. Concave n-gonlar ear-clipping ile üçgenleniyor. Böylece dudak altına/üstüne uzayan uzun üçgen “spike” temizlendi.
- Ağır subdivision yalnızca ağız parçalarına uygulanır; modelin kalanını gereksiz yere milyonlarca poligona şişirmez.

V7 INTERPOLASYON + RENK FILTRESI
---------------------------------
- Smooth artik Blockbench mantigindaki Catmull-Rom / cubic Hermite spline kullanir.
- Smooth keyframe ara noktalarda sifir hiza zorlanmaz; komsu keylerden tangent tasir.
- Linear tamamen duz ve sabit hizli gecistir.
- Step, sonraki keyframe'e kadar onceki degeri tutar ve keyframe'in tam ustunde aninda yeni degere gecer.
- Bir segmentin iki ucundan biri Smooth ise Blockbench gibi Catmull-Rom uygulanir.
- Rotation kanallarinda 179 -> -179 gibi acilar shortest-path acilarak ani 358 derece donus engellenir.
- Renk filtresi artik gercek colorize filtresi gibi golgelendirmeyi korur.
- Renk secince filtre gucu 0 ise otomatik %80'e acilir; slider ile ayarlanabilir.


Bu paket, paketteki models/baldi_source.an8 kaynağını browserda düzenlenebilir bir
parça/rig hiyerarşisine dönüştüren offline animasyon stüdyosudur.

BAŞLATMA
--------
1) START.bat çalıştır veya index.html dosyasını Chrome / Edge ile aç.
2) Model açıldığında soldaki hiyerarşiden bir parçaya tıkla.
3) G = Position, R = Rotation, S = Scale, Q/Esc = seçim.
4) Auto Key açıkken parçayı hareket ettirdiğinde o parçanın ilgili transform
   kanalına otomatik keyframe yazılır.

V6 BLOCKBENCH TARZI TIMELINE
-----------------------------
- Timeline artık animasyonlu bütün parçaları isimleriyle alt alta gösterir. Her parçanın altında
  Position / Rotation / Scale satırları bulunur. Parça başlığındaki oka tıklayarak satırları
  açıp kapatabilirsin.
- Boş timeline alanında sol tuşla kutu çizerek birden fazla keyframe seçebilirsin. Ctrl veya
  Shift basılıyken mevcut seçime ekleme yapılır.
- Seçili keyframe elmaslarından birini sürüklersen bütün seçili keyler beraber sağa/sola taşınır.
- Ctrl+C = keyleri kopyala, Ctrl+V = mevcut frame'den başlayarak yapıştır, Ctrl+X = kes,
  Delete/Backspace = seçili keyleri sil. Timeline odaktayken Ctrl+A bütün görünen animasyon
  keylerini seçer.
- Kopyalama parça adını, Position/Rotation/Scale kanalını, eksen değerlerini, interpolation
  tipini ve keyler arası relatif frame farkını korur. Böylece bir kol hareketini topluca başka
  bir zamana yapıştırabilirsin.
- Timeline'da kanalın boş bir frame'ine çift tıklamak o parça/kanal için anında key ekler.
- Seçili key sayısı transport bar'da görünür. Interpolation menüsü çoklu seçili keylere de
  topluca uygulanır.

V5 ANA DÜZELTMELER
------------------
- Rotation interpolasyonu artık açıları 360° üzerinden körlemesine lerp etmez; en kısa
  açı yolunu kullanır. Eski Catmull overshoot kaldırıldı. Smooth/Corner/Linear/Step
  artık tahmin edilebilir ve birbirinden farklı davranır.
- Interpolation menüsünü bir keyframe üzerindeyken değiştirirsen seçili parçanın o
  framedeki keyleri de anında güncellenir.
- Gizmo eksenleri dünya eksenine sabit çizilmez. Parent/local transform ve mevcut
  Euler rotasyon sırasına göre gerçek hareket/rotation/scale eksenlerinden çizilir.
- Rotation gizmo drag'i 2D ekran açısına göre değil mouse ray + gerçek 3D rotation
  plane kesişimine göre hesaplanır. Bu, küçük hareketlerde ani yön atlamalarını giderir.
- Gizmo pivot merkezi artık parçanın animasyonlu Position değerini de takip eder.
- Timeline scrub window-level pointer tracking + RAF throttling kullanır. Basılı tutup
  canvas dışına doğru sürüklerken bile ileri/geri sarma devam eder.
- GIF frame disposal method 2 kullanır. Şeffaf frame'lerde önceki karelerin üst üste
  birikmesi/ghosting sorunu giderildi.
- Render aralığında “Bitişi otomatik son keyframe yap” varsayılan açıktır. Frame step
  son keyframe'e tam bölünmese bile son keyframe ayrıca mutlaka render edilir.
- Stabil video modu WebCodecs VP9/VP8 + kendi WebM muxer'ını kullanır. Karelere gerçek
  timestamp verildiği için MediaRecorder'ın realtime yetişemeyip frame dondurması
  yaşanmaz. Tarayıcı desteklemiyorsa eski MP4/WebM MediaRecorder fallback'i vardır.
- Anim8or object-local materyalleri artık object adına göre scope edilir. Aynı
  isimli materyaller başka objectlerden yanlışlıkla birbirine karışmaz.
- Mouth2 içindeki kaynakta bulunan küçük orphan/default yüz grubu filtrelendi.
  Dudağın yakınında görünen parser kaynaklı çıkıntı giderildi.
- Parmak meshleri Figure joint pivotlarına bind edilir. Kaynaktaki primitive
  tabanlarının jointten birkaç unit uzakta durması nedeniyle oluşan "havada
  parmak" görüntüsü düzeltilir.
- Sol tık + sürük = kamera pan. Model üstünde sadece tıklarsan parçayı seçer,
  sürüklersen seçimi bozmadan kamerayı taşır.
- Sağ tık + sürük = orbit. Mouse wheel = zoom.
- Blender benzeri gizmolarda X/Y/Z eksenleri, rotation halkaları, scale
  tutamaçları ve center handle bulunur. Mouse ile üzerine gelinen eksen sarı
  highlight olur.
- Timeline pointer-capture ile scrub edilir. Sol tuşa basılı tutup sağa/sola
  sürükleyerek frame ileri/geri sarılır.
- PNG / PNG Frames ZIP / Sprite Sheet artık export canvasını viewport boyutuna
  geri küçültmez. Gerçek seçili çözünürlükte render edilir.
- Render kadrajı en-boy oranına göre hesaplanır. "Tüm modeli sabit sığdır"
  seçeneği bütün export frame aralığının bounds'unu tek seferde hesaplar; kareler
  arasında zoom pompalaması olmaz ve model ezilmez.
- Hazır çözünürlükler: 480x360, 720p, 1080p, 1440p/2K, 4K UHD ve 1024 square.
- GIF LZW encoder güvenilirlik için periyodik dictionary clear kullanır. Önceki
  sürümde görülebilen rastgele palette/rainbow bozulmaları giderildi.
- Video export önce MP4/H.264 MediaRecorder desteğini dener; tarayıcı desteklemiyorsa
  VP9/VP8 WebM'e otomatik düşer.
- Sağ Inspector içinde parçaya özel Tint, Tint Strength, Brightness ve Opacity
  vardır. Bunlar kaynak .an8 / GLB materyalini değiştirmez, yalnız parça üstüne
  görünüm filtresi uygular.
- Hiyerarşide +Mesh ile Cube/Sphere/Cylinder/Plane eklenebilir.
- +GLB ile binary glTF 2.0 (.glb) eklenebilir. Node hiyerarşisi korunur; node ve
  mesh parçaları diğer Baldi parçaları gibi seçilir, G/R/S yapılır ve Auto Key
  ile animasyonlanır.
- GLB PBR baseColorFactor ve gömülü baseColor texture desteği bulunur.
- GLB skin varsa JOINTS_0 + WEIGHTS_0 dominant bone'a göre rigid segmentlere
  ayrılır. Bu stüdyonun sprite/parça animasyon mantığına uygundur. Tam smooth
  vertex skin deformation değildir.
- Proje formatı v2: sonradan eklenen primitive/GLB parçaları, parça filtreleri ve
  gömülü GLB texture verileri proje JSON'una kaydedilir.

KAMERA
------
Sol tık + sürük     Orbit
Sağ tık + sürük    Kamera pan
Orta tık            Orbit
Shift + orta tık    Pan
Alt + sol tık       Orbit
Mouse wheel         Zoom
Tek sol tık model   Gerçek GPU triangle picking ile parçayı seç

TRANSFORM / KEYFRAME
--------------------
G        Position
R        Rotation
S        Scale
Q / Esc  Select
K        Seçili parçanın Position + Rotation + Scale kanallarına key ekle
Space    Play / Pause
← / →    Bir frame geri / ileri

Auto Key açıksa örneğin frame 15'te RArm1 seçip R ile döndürmek doğrudan o
parçanın Rotation key'ini oluşturur. İlk hareket frame 0'dan sonra yapılırsa
başlangıç pozu korunması için frame 0 key'i otomatik eklenir.

INTERPOLASYON
-------------
Smooth
Corner
Linear
Step

Timeline üç transform satırı gösterir: POSITION, ROTATION, SCALE. Curve Editor
RX/RY/RZ/TX/TY/TZ/SX/SY/SZ kanallarını ayrı incelemek için kullanılabilir.

PARÇA GÖRÜNÜM FİLTRESİ
----------------------
Tint            Seçili parçaya uygulanacak filtre rengi
Filtre gücü     0 = orijinal materyal, 1 = tamamen tint
Brightness      Parçaya özel parlaklık çarpanı
Opacity         Parçaya özel alfa

Bu ayarlar kaynak materyal tablolarını değiştirmez. Aynı materyali kullanan başka
parçaların rengi etkilenmez.

MESH EKLEME
-----------
Hiyerarşi > + Mesh
- Cube
- Sphere
- Cylinder
- Plane

Yeni mesh seçili parçanın child'ı olur. Oluşturulduktan sonra normal bir parça
gibi transform, parent, görünürlük, filtre ve keyframe alır.

GLB EKLEME
----------
Hiyerarşi > + GLB
- Binary glTF 2.0 (.glb)
- Triangle primitive (mode 4)
- Node hierarchy
- Position / Normal / UV
- PBR base color
- Embedded image bufferView veya data URI texture
- JOINTS_0 / WEIGHTS_0 varsa dominant-bone rigidization

Line/point/triangle-strip gibi non-triangle primitive modları bu sürümde atlanır.
GLB node'ları hiyerarşide mor GLB etiketiyle görünür.

RENDER
------
Hazır çözünürlükler:
Baldi Classic   480 x 360   4:3
HD 720p        1280 x 720  16:9
Full HD        1920 x 1080 16:9
1440p / 2K     2560 x 1440 16:9
4K UHD         3840 x 2160 16:9
Square         1024 x 1024 1:1

Render kadrajı:
- Kameradaki görünüm: viewport kamerasını aynen kullanır.
- Tüm modeli sabit sığdır: bütün export frame aralığını tek sabit kadraja alır.
- Seçili parçayı sığdır: seçili parça için sabit kadraj oluşturur.

Çıktılar:
PNG Frame
PNG Frames ZIP
Sprite Sheet PNG
Animated GIF
MP4 veya WebM Video

4K GIF veya çok uzun 4K frame dizileri doğal olarak çok RAM kullanır. Bu bir
codec mucizesi değil, milyonlarca pikselin insanlığın ısrarıyla tekrar tekrar
saklanmasıdır. PNG/MP4 böyle durumlarda daha pratiktir.

DOSYALAR
--------
index.html                     Ana arayüz
style.css                      Arayüz stilleri
app.js                         Rig, animation, gizmo, camera, GLB, export sistemi
model-data.js                  .an8 kaynağından Figure-bind derlenmiş model
models/baldi_source.an8        Gönderilen ham Anim8or kaynak modeli
models/reference.png           Model referans görüntüsü
tools/compile_an8.py           .an8 -> model-data.js derleyici
tools/rebuild_model.bat        Modeli yeniden derlemek için yardımcı
examples/wave_project.json     Örnek wave projesi
START.bat                      Siteyi açar

MODELİ YENİDEN DERLEME
----------------------
models/baldi_source.an8 dosyasını Anim8or'da değiştirdikten sonra:
  tools/rebuild_model.bat
çalıştır. Python 3 gerektirir.

NOT
---
Bu bir Anim8or executable klonu değildir. Paket içindeki gerçek .an8 modelini
web animasyon/sprite iş akışına çeviren özel bir stüdyodur. Kaynak model dosyası
ZIP'in içinde aynen tutulur.


V10:
- Kamera mouse kontrolleri ters çevrildi: sol sürük orbit, sağ sürük pan.
- Timeline frame/tick cetveli dikey scroll sırasında artık sticky kalır ve her zaman timeline panelinin üstünde görünür.
- Sticky cetvel üzerinden basılı tutup scrub yapılabilir; Shift+wheel zoom da çalışır.
