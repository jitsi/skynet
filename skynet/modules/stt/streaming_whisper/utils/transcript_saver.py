import asyncio
import json
import os
import time
from datetime import datetime
from typing import List, Optional

from skynet.env import (
    streaming_whisper_save_transcripts,
    streaming_whisper_output_dir,
    streaming_whisper_output_formats,
    streaming_whisper_flush_interval_ms
)
from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.utils.utils import TranscriptionResponse

log = get_logger(__name__)


class TranscriptSaver:
    def __init__(self, meeting_id: str):
        self.meeting_id = meeting_id
        self.transcripts: List[TranscriptionResponse] = []
        self.last_flush_time = time.time()
        self.flush_task: Optional[asyncio.Task] = None
        
        if streaming_whisper_save_transcripts:
            os.makedirs(streaming_whisper_output_dir, exist_ok=True)
            self._start_flush_task()
    
    def _start_flush_task(self):
        """Periyodik olarak transcriptleri dosyaya kaydetmek için task başlatır"""
        if self.flush_task is None or self.flush_task.done():
            self.flush_task = asyncio.create_task(self._periodic_flush())
    
    async def _periodic_flush(self):
        """Belirli aralıklarla transcriptleri dosyaya kaydeder"""
        while True:
            try:
                await asyncio.sleep(streaming_whisper_flush_interval_ms / 1000)
                await self.flush_transcripts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Periodic flush error for meeting {self.meeting_id}: {e}")
    
    def add_transcript(self, transcript: TranscriptionResponse):
        """Yeni transcript ekler"""
        if streaming_whisper_save_transcripts:
            self.transcripts.append(transcript)
            log.debug(f"Added transcript for meeting {self.meeting_id}: {transcript.text}")
    
    async def flush_transcripts(self):
        """Mevcut transcriptleri dosyaya kaydeder"""
        if not streaming_whisper_save_transcripts or not self.transcripts:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for format_type in streaming_whisper_output_formats:
                if format_type == 'jsonl':
                    await self._save_jsonl(timestamp)
                elif format_type == 'srt':
                    await self._save_srt(timestamp)
                elif format_type == 'txt':
                    await self._save_txt(timestamp)
            
            # Kaydedilen transcriptleri temizle
            self.transcripts.clear()
            self.last_flush_time = time.time()
            
        except Exception as e:
            log.error(f"Error flushing transcripts for meeting {self.meeting_id}: {e}")
    
    async def _save_jsonl(self, timestamp: str):
        """JSONL formatında transcriptleri kaydeder"""
        filename = f"{self.meeting_id}_{timestamp}.jsonl"
        filepath = os.path.join(streaming_whisper_output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for transcript in self.transcripts:
                json.dump(transcript.model_dump(), f, ensure_ascii=False)
                f.write('\n')
        
        log.info(f"Saved {len(self.transcripts)} transcripts to {filepath}")
    
    async def _save_srt(self, timestamp: str):
        """SRT formatında transcriptleri kaydeder"""
        filename = f"{self.meeting_id}_{timestamp}.srt"
        filepath = os.path.join(streaming_whisper_output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for i, transcript in enumerate(self.transcripts, 1):
                # Timestamp'i SRT formatına çevir
                start_time = self._format_timestamp(transcript.ts)
                end_time = self._format_timestamp(transcript.ts + 5000)  # 5 saniye varsayım
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"[{transcript.participant_id}] {transcript.text}\n")
                f.write("\n")
        
        log.info(f"Saved {len(self.transcripts)} transcripts to {filepath}")
    
    async def _save_txt(self, timestamp: str):
        """TXT formatında transcriptleri kaydeder"""
        filename = f"{self.meeting_id}_{timestamp}.txt"
        filepath = os.path.join(streaming_whisper_output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for transcript in self.transcripts:
                timestamp_str = self._format_timestamp(transcript.ts)
                f.write(f"[{timestamp_str}] [{transcript.participant_id}]: {transcript.text}\n")
        
        log.info(f"Saved {len(self.transcripts)} transcripts to {filepath}")
    
    def _format_timestamp(self, ms: int) -> str:
        """Milisaniyeyi SRT timestamp formatına çevirir"""
        seconds = ms // 1000
        milliseconds = ms % 1000
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    async def finalize(self):
        """Meeting sonlandığında son transcriptleri kaydeder ve cleanup yapar"""
        if streaming_whisper_save_transcripts:
            await self.flush_transcripts()
            
            if self.flush_task and not self.flush_task.done():
                self.flush_task.cancel()
                try:
                    await self.flush_task
                except asyncio.CancelledError:
                    pass
            
            log.info(f"Finalized transcript saving for meeting {self.meeting_id}") 