# Monitoring

Skynet exposes a Prometheus `/metrics` endpoint on port `8001`.

The metrics endpoint can be disabled by setting the `ENABLE_METRICS` env var to `false`.

## Exposed metrics

```
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 0.0
python_gc_objects_collected_total{generation="1"} 0.0
python_gc_objects_collected_total{generation="2"} 0.0
# HELP python_gc_objects_uncollectable_total Uncollectable objects found during GC
# TYPE python_gc_objects_uncollectable_total counter
python_gc_objects_uncollectable_total{generation="0"} 0.0
python_gc_objects_uncollectable_total{generation="1"} 0.0
python_gc_objects_uncollectable_total{generation="2"} 0.0
# HELP python_gc_collections_total Number of times this generation was collected
# TYPE python_gc_collections_total counter
python_gc_collections_total{generation="0"} 0.0
python_gc_collections_total{generation="1"} 0.0
python_gc_collections_total{generation="2"} 0.0
# HELP python_info Python platform information
# TYPE python_info gauge
python_info{implementation="CPython",major="3",minor="11",patchlevel="7",version="3.11.7"} 1.0
# HELP process_virtual_memory_bytes Virtual memory size in bytes.
# TYPE process_virtual_memory_bytes gauge
process_virtual_memory_bytes 0.0
# HELP process_resident_memory_bytes Resident memory size in bytes.
# TYPE process_resident_memory_bytes gauge
process_resident_memory_bytes 0.0
# HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
# TYPE process_start_time_seconds gauge
process_start_time_seconds 0.0
# HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
# TYPE process_cpu_seconds_total counter
process_cpu_seconds_total 0.0
# HELP process_open_fds Number of open file descriptors.
# TYPE process_open_fds gauge
process_open_fds 0.0
# HELP process_max_fds Maximum number of open file descriptors.
# TYPE process_max_fds gauge
process_max_fds 0.0
# HELP Skynet_Summaries_summary_input_length Measures the length of the input text
# TYPE Skynet_Summaries_summary_input_length histogram
Skynet_Summaries_summary_input_length_bucket{le="50.0"} 0.0
Skynet_Summaries_summary_input_length_bucket{le="100.0"} 0.0
Skynet_Summaries_summary_input_length_bucket{le="500.0"} 0.0
Skynet_Summaries_summary_input_length_bucket{le="1000.0"} 0.0
Skynet_Summaries_summary_input_length_bucket{le="2000.0"} 0.0
Skynet_Summaries_summary_input_length_bucket{le="5000.0"} 0.0
Skynet_Summaries_summary_input_length_bucket{le="10000.0"} 0.0
Skynet_Summaries_summary_input_length_bucket{le="+Inf"} 0.0
Skynet_Summaries_summary_input_length_count 0.0
Skynet_Summaries_summary_input_length_sum 0.0
# HELP Skynet_Summaries_summary_input_length_created Measures the length of the input text
# TYPE Skynet_Summaries_summary_input_length_created gauge
Skynet_Summaries_summary_input_length_created 0.0
# HELP Skynet_Summaries_summary_duration_seconds Measures the duration of the summary / action items inference in seconds
# TYPE Skynet_Summaries_summary_duration_seconds histogram
Skynet_Summaries_summary_duration_seconds_bucket{le="1.0"} 0.0
Skynet_Summaries_summary_duration_seconds_bucket{le="5.0"} 0.0
Skynet_Summaries_summary_duration_seconds_bucket{le="25.0"} 0.0
Skynet_Summaries_summary_duration_seconds_bucket{le="125.0"} 0.0
Skynet_Summaries_summary_duration_seconds_bucket{le="+Inf"} 0.0
Skynet_Summaries_summary_duration_seconds_count 0.0
Skynet_Summaries_summary_duration_seconds_sum 0.0
# HELP Skynet_Summaries_summary_duration_seconds_created Measures the duration of the summary / action items inference in seconds
# TYPE Skynet_Summaries_summary_duration_seconds_created gauge
Skynet_Summaries_summary_duration_seconds_created 0.0
# HELP Skynet_Summaries_summary_queue_time_seconds Measures the time spent in the queue in seconds
# TYPE Skynet_Summaries_summary_queue_time_seconds histogram
Skynet_Summaries_summary_queue_time_seconds_bucket{le="1.0"} 0.0
Skynet_Summaries_summary_queue_time_seconds_bucket{le="5.0"} 0.0
Skynet_Summaries_summary_queue_time_seconds_bucket{le="25.0"} 0.0
Skynet_Summaries_summary_queue_time_seconds_bucket{le="125.0"} 0.0
Skynet_Summaries_summary_queue_time_seconds_bucket{le="+Inf"} 0.0
Skynet_Summaries_summary_queue_time_seconds_count 0.0
Skynet_Summaries_summary_queue_time_seconds_sum 0.0
# HELP Skynet_Summaries_summary_queue_time_seconds_created Measures the time spent in the queue in seconds
# TYPE Skynet_Summaries_summary_queue_time_seconds_created gauge
Skynet_Summaries_summary_queue_time_seconds_created 0.0
# HELP Skynet_Summaries_summary_queue_size Number of jobs in the queue
# TYPE Skynet_Summaries_summary_queue_size gauge
Skynet_Summaries_summary_queue_size 0.0
# HELP Skynet_Streaming_Whisper_LiveWsConnections Number of active WS connections
# TYPE Skynet_Streaming_Whisper_LiveWsConnections gauge
Skynet_Streaming_Whisper_LiveWsConnections 0.0
# HELP Skynet_Streaming_Whisper_WhisperTranscriptionDuration Measures the duration of the transcription process in seconds
# TYPE Skynet_Streaming_Whisper_WhisperTranscriptionDuration histogram
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.1"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.2"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.3"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.4"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.5"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.6"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.7"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.8"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="0.9"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.0"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.1"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.2"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.3"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.4"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.5"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.6"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.7"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.8"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="1.9"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.0"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.1"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.2"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.3"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.4"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.5"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.6"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.7"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.8"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="2.9"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="3.0"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_bucket{le="+Inf"} 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_count 0.0
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_sum 0.0
# HELP Skynet_Streaming_Whisper_WhisperTranscriptionDuration_created Measures the duration of the transcription process in seconds
# TYPE Skynet_Streaming_Whisper_WhisperTranscriptionDuration_created gauge
Skynet_Streaming_Whisper_WhisperTranscriptionDuration_created 0.0
# HELP Skynet_Summaries_forced_exit_total Number of forced exits
# TYPE Skynet_Summaries_forced_exit_total counter
Skynet_Summaries_forced_exit_total 0.0
# HELP Skynet_Summaries_forced_exit_created Number of forced exits
# TYPE Skynet_Summaries_forced_exit_created gauge
Skynet_Summaries_forced_exit_created 0.0
# HELP http_request_duration_seconds Duration of HTTP requests in seconds
# TYPE http_request_duration_seconds histogram
# HELP Skynet_Summaries_http_requests_total Total number of requests by method, status and handler.
# TYPE Skynet_Summaries_http_requests_total counter
```
