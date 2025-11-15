# note_system.py
import json

class Note:
    """개별 노트의 정보를 담는 데이터 클래스 (Hold 노트 상태 강화)"""
    def __init__(self, spawn_time, target_pose, note_type='tap', duration=0):
        self.spawn_time = spawn_time
        self.target_pose = target_pose
        self.note_type = note_type
        self.duration = duration
        
        self.is_judged = False      # 시작 판정이 끝났는지 여부
        self.is_holding = False     # 현재 성공적으로 홀드 중인지 여부
        self.is_failed = False      # 홀드에 실패했는지 여부 (중요)
        self.y_pos = 0

class NoteController:
    """비트맵을 로드하고 노트의 생성 및 이동을 관리하는 클래스"""
    def __init__(self, beatmap_file, speed=300):
        self.beatmap_file = beatmap_file
        self.note_speed = speed 
        self.beatmap = self._load_beatmap(self.beatmap_file)
        self.notes = []
        self.spawn_index = 0

    def _load_beatmap(self, beatmap_file):
        try:
            with open(beatmap_file, 'r') as f:
                data = json.load(f)
                return sorted(data['notes'], key=lambda x: x['time'])
        except FileNotFoundError:
            print(f"Error: Beatmap file '{beatmap_file}' not found.")
            return []
    
    def reset(self):
        self.notes = []
        self.spawn_index = 0
        self.beatmap = self._load_beatmap(self.beatmap_file)

    def update(self, game_time, delta_time):
        if self.spawn_index < len(self.beatmap):
            note_data = self.beatmap[self.spawn_index]
            if game_time >= note_data['time']:
                new_note = Note(
                    note_data['time'],
                    note_data['pose'],
                    note_data.get('type', 'tap'),
                    note_data.get('duration', 0)
                )
                self.notes.append(new_note)
                self.spawn_index += 1

        for note in self.notes:
            note.y_pos += self.note_speed * delta_time