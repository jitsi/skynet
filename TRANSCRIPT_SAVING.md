# Transcript Kaydetme Özelliği

Bu özellik, canlı transcriptleri otomatik olarak dosyaya kaydetmenizi sağlar. Transcriptler JSONL, SRT ve TXT formatlarında kaydedilebilir.

## Özellikler

- **Çoklu Format Desteği**: JSONL, SRT, TXT formatlarında kaydetme
- **Otomatik Dosya Yönetimi**: Meeting ID ve timestamp ile otomatik dosya adlandırma
- **Periyodik Kaydetme**: Belirli aralıklarla otomatik kaydetme
- **Meeting Sonlandırma**: Meeting bittiğinde son transcriptleri kaydetme

## Environment Değişkenleri

`compose-dev.yaml` dosyasında aşağıdaki environment değişkenlerini ayarlayabilirsiniz:

```yaml
environment:
  # Transcript kaydetme özelliğini etkinleştir
  - STREAMING_WHISPER_SAVE_TRANSCRIPTS=true
  
  # Kaydedilecek dosyaların dizini (container içinde)
  - STREAMING_WHISPER_OUTPUT_DIR=/opt/transcripts
  
  # Kaydedilecek formatlar (virgülle ayrılmış)
  - STREAMING_WHISPER_OUTPUT_FORMATS=jsonl,srt,txt
  
  # Periyodik kaydetme aralığı (milisaniye)
  - STREAMING_WHISPER_FLUSH_INTERVAL_MS=10000
```

## Volume Mount

Transcript dosyalarının host makinede erişilebilir olması için volume mount yapılandırması:

```yaml
volumes:
  # Local transcripts klasörünü container'a mount et
  - ./transcripts:/opt/transcripts
```

## Desteklenen Formatlar

### 1. JSONL Format
Her satırda bir transcript JSON objesi:
```json
{"id": "1", "participant_id": "user1", "ts": 1000, "text": "Merhaba", "audio": "", "type": "final", "variance": 0.95}
{"id": "2", "participant_id": "user2", "ts": 5000, "text": "Evet", "audio": "", "type": "final", "variance": 0.88}
```

### 2. SRT Format
Subtitle formatı:
```
1
00:00:01,000 --> 00:00:06,000
[user1] Merhaba

2
00:00:05,000 --> 00:00:10,000
[user2] Evet
```

### 3. TXT Format
Basit metin formatı:
```
[00:00:01,000] [user1]: Merhaba
[00:00:05,000] [user2]: Evet
```

## Dosya Adlandırma

Dosyalar şu formatta adlandırılır:
```
{meeting_id}_{timestamp}.{format}
```

Örnek:
- `meeting_123_20250806_031304.jsonl`
- `meeting_123_20250806_031304.srt`
- `meeting_123_20250806_031304.txt`

## Kullanım

1. **Docker Compose ile çalıştırma**:
   ```bash
   docker compose -f compose-dev.yaml up --build
   ```

2. **Local çalıştırma**:
   ```bash
   # Environment değişkenlerini ayarla
   export STREAMING_WHISPER_SAVE_TRANSCRIPTS=true
   export STREAMING_WHISPER_OUTPUT_DIR=./transcripts
   export STREAMING_WHISPER_OUTPUT_FORMATS=jsonl,srt,txt
   export STREAMING_WHISPER_FLUSH_INTERVAL_MS=10000
   
   # Uygulamayı çalıştır
   python -m skynet.main
   ```

3. **WebSocket bağlantısı**:
   ```
   ws://localhost:8000/streaming-whisper/ws/{meeting_id}
   ```

## Örnek Çıktı

Transcript kaydetme özelliği etkinleştirildiğinde, `transcripts` klasöründe aşağıdaki gibi dosyalar oluşacaktır:

```
transcripts/
├── meeting_123_20250806_031304.jsonl
├── meeting_123_20250806_031304.srt
└── meeting_123_20250806_031304.txt
```

## Notlar

- Transcript kaydetme özelliği sadece "final" tipindeki transcriptleri kaydeder
- Periyodik kaydetme aralığı çok kısa tutulmamalıdır (performans için)
- Dosya yazma izinlerinin doğru ayarlandığından emin olun
- Büyük meetingler için disk alanını kontrol edin

## Sorun Giderme

### Transcriptler kaydedilmiyor
1. `STREAMING_WHISPER_SAVE_TRANSCRIPTS=true` olduğundan emin olun
2. `STREAMING_WHISPER_OUTPUT_DIR` dizininin yazılabilir olduğunu kontrol edin
3. Volume mount'un doğru yapılandırıldığını kontrol edin

### Dosya formatı sorunları
1. `STREAMING_WHISPER_OUTPUT_FORMATS` değerinin doğru olduğunu kontrol edin
2. Desteklenen formatlar: `jsonl`, `srt`, `txt`

### Performans sorunları
1. `STREAMING_WHISPER_FLUSH_INTERVAL_MS` değerini artırın
2. Gereksiz formatları kaldırın
3. Disk I/O performansını kontrol edin 