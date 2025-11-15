# note_system.py
# 이 파일의 내용을 아래 코드로 전체 교체하세요.
import json

class Note:
    """스와이프 노트 유예 시간 타이머 추가"""
    def __init__(self, spawn_time, target_pose, note_type='tap', duration=0, direction=None):
        self.spawn_time = spawn_time
        self.target_pose = target_pose
        self.note_type = note_type
        self.duration = duration
        self.direction = direction
        
        # <<< 추가된 부분: 스와이프 포즈 유지를 위한 유예 시간 타이머
        self.swipe_pose_grace_timer = 0.0

        self.is_judged = False
        self.is_holding = False
        self.is_swiping = False
        self.is_failed = False
        self.y_pos = 0

class NoteController:
    # 이 클래스는 변경 사항이 없습니다. 이전 버전과 동일합니다.
    def __init__(self, beatmap_file, speed=300):
        self.beatmap_file = beatmap_file; self.note_speed = speed 
        self.beatmap = self._load_beatmap(self.beatmap_file)
        self.notes = []; self.spawn_index = 0
    def _load_beatmap(self, beatmap_file):
        try:
            with open(beatmap_file, 'r') as f: return sorted(json.load(f)['notes'], key=lambda x: x['time'])
        except FileNotFoundError: print(f"Error: Beatmap file '{beatmap_file}' not found."); return []
    def reset(self):
        self.notes = []; self.spawn_index = 0
        self.beatmap = self._load_beatmap(self.beatmap_file)
    def update(self, game_time, delta_time):
        if self.spawn_index < len(self.beatmap):
            note_data = self.beatmap[self.spawn_index]
            if game_time >= note_data['time']:
                new_note = Note(note_data['time'], note_data['pose'], note_data.get('type', 'tap'), note_data.get('duration', 0), note_data.get('direction', None))
                self.notes.append(new_note)
                self.spawn_index += 1
        for note in self.notes:
            if note.note_type == 'swipe' and note.is_swiping: continue
            note.y_pos += self.note_speed * delta_time