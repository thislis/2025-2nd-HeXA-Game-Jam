class JudgementEngine:
    """노트와 플레이어 입력을 비교하여 판정을 내리는 클래스 (Hold 노트 로직 추가)"""
    # 1. __init__ 메소드가 3개의 인자를 받도록 수정합니다.
    def __init__(self, line_y, thresholds, note_speed):
        self.judgement_line_y = line_y
        self.thresholds = thresholds
        self.note_speed = note_speed

    def check_judgements(self, notes, current_pose, delta_time):
        """판정선 근처의 노트를 확인하고 판정 결과를 반환합니다."""
        judgements = []
        
        for note in notes:
            if note.note_type == 'tap':
                if note.is_judged:
                    continue
                self._judge_tap_note(note, current_pose, judgements)
            
            elif note.note_type == 'hold':
                self._judge_hold_note(note, current_pose, delta_time, judgements)

            # 판정선을 한참 지나쳐버린 노트 처리 (MISS)
            if not note.is_judged and note.y_pos > self.judgement_line_y + self.thresholds['GREAT']:
                note.is_judged = True
                judgements.append({'judgement': 'MISS', 'note': note})
        
        return judgements

    def _judge_tap_note(self, note, current_pose, judgements):
        distance = abs(note.y_pos - self.judgement_line_y)
        if distance <= self.thresholds['GREAT']:
            judgement = 'MISS'
            if note.target_pose == current_pose:
                judgement = 'PERFECT' if distance <= self.thresholds['PERFECT'] else 'GREAT'
            
            note.is_judged = True
            judgements.append({'judgement': judgement, 'note': note})

    def _judge_hold_note(self, note, current_pose, delta_time, judgements):
        hold_length_pixels = note.duration * self.note_speed
        note_head_y = note.y_pos
        note_tail_y = note.y_pos - hold_length_pixels

        # Hold 시작 판정
        if not note.is_judged and abs(note_head_y - self.judgement_line_y) <= self.thresholds['GREAT']:
            judgement = 'MISS'
            if note.target_pose == current_pose:
                distance = abs(note_head_y - self.judgement_line_y)
                judgement = 'PERFECT' if distance <= self.thresholds['PERFECT'] else 'GREAT'
                note.is_holding = True # 홀드 시작 성공
            
            note.is_judged = True
            judgements.append({'judgement': judgement, 'note': note})

        # Hold 유지 판정
        elif note.is_holding:
            # 홀드 노트의 몸통이 판정선 위에 있을 때
            if note_tail_y < self.judgement_line_y < note_head_y:
                if note.target_pose != current_pose:
                    # 포즈를 놓쳤을 경우
                    note.is_holding = False
                    judgements.append({'judgement': 'HOLD_BREAK', 'note': note})
            # 홀드 종료
            elif note_tail_y > self.judgement_line_y:
                note.is_holding = False # 정상적으로 홀드 종료
                judgements.append({'judgement': 'HOLD_END', 'note': note})