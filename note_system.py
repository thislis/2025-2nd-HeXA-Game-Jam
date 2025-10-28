import json

class Note:
    """개별 노트의 정보를 담는 데이터 클래스"""
    def __init__(self, spawn_time, target_pose, note_type='tap'):
        self.spawn_time = spawn_time
        self.target_pose = target_pose
        self.note_type = note_type
        self.is_active = False
        self.is_judged = False
        self.y_pos = 0 # 화면 상단에서 시작

class NoteController:
    """비트맵을 로드하고 노트의 생성 및 이동을 관리하는 클래스"""
    def __init__(self, beatmap_file, speed=300):
        self.beatmap = self._load_beatmap(beatmap_file)
        self.notes = []
        self.spawn_index = 0
        self.note_speed = speed # pixels per second

    def _load_beatmap(self, beatmap_file):
        try:
            with open(beatmap_file, 'r') as f:
                data = json.load(f)
                # 시간을 기준으로 비트맵 정렬
                return sorted(data['notes'], key=lambda x: x['time'])
        except FileNotFoundError:
            print(f"Error: Beatmap file '{beatmap_file}' not found.")
            return []

    def update(self, game_time, delta_time):
        """게임 시간에 따라 노트를 생성하고 위치를 업데이트합니다."""
        # 노트 생성
        if self.spawn_index < len(self.beatmap):
            note_data = self.beatmap[self.spawn_index]
            if game_time >= note_data['time']:
                new_note = Note(note_data['time'], note_data['pose'], note_data.get('type', 'tap'))
                self.notes.append(new_note)
                self.spawn_index += 1

        # 노트 이동 및 제거
        for note in self.notes:
            note.y_pos += self.note_speed * delta_time

        # 화면을 벗어난 노트 제거 (MISS 처리)
        # 이 로직은 JudgementEngine에서 처리하는 것이 더 적합함
        self.notes = [note for note in self.notes if note.y_pos < 700]