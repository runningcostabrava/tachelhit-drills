import sys
sys.path.append('.')
from srt_parser import parse_srt_content

# Test SRT content
test_srt = '''1
00:02:28,000 --> 00:02:30,000
7aa-+a52t 34-7

2
00:02:30,000 --> 00:02:32,000
7aa#6a52t5a78.3$

3
00:02:36,000 --> 00:02:38,000
3 Hi ha perills per a mi

4
00:02:38,000 --> 00:02:40,000
La situació. El bo s'ha despertat'''

segments = parse_srt_content(test_srt)
print(f'Parsed {len(segments)} segments:')
for i, seg in enumerate(segments):
    print(f'{i+1}. Start: {seg["start_time"]}, Text: {seg["text"][:50]}...')