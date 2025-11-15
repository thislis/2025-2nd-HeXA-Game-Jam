# judgement_engine.py
# 이 파일의 내용을 아래 코드로 전체 교체하세요.

class JudgementEngine:
    def __init__(self, line_y, thresholds, note_speed):
        self.judgement_line_y = line_y
        self.thresholds = thresholds
        self.note_speed = note_speed

    def check_judgements(self, notes, current_pose):
        judgements = []
        
        for note in notes:
            if note.is_failed:
                continue

            if note.note_type == 'tap':
                if not note.is_judged:
                    self._judge_tap_note(note, current_pose, judgements)
            
            elif note.note_type == 'hold':
                self._judge_hold_note(note, current_pose, judgements)

            # 판정선을 한참 지나쳐버린 노트 처리 (MISS)
            if not note.is_judged and note.y_pos > self.judgement_line_y + self.thresholds['GREAT']:
                note.is_judged = True
                note.is_failed = True
                judgements.append({'judgement': 'MISS', 'note': note})
        
        return judgements

    def _judge_tap_note(self, note, current_pose, judgements):
        distance = abs(note.y_pos - self.judgement_line_y)
        if distance <= self.thresholds['GREAT']:
            note.is_judged = True
            if note.target_pose == current_pose:
                judgement = 'PERFECT' if distance <= self.thresholds['PERFECT'] else 'GREAT'
            else:
                judgement = 'MISS'
                note.is_failed = True
            
            judgements.append({'judgement': judgement, 'note': note})

    def _judge_hold_note(self, note, current_pose, judgements):
        hold_length_pixels = note.duration * self.note_speed
        note_head_y = note.y_pos
        note_tail_y = note.y_pos - hold_length_pixels

        # --- Phase 1: 홀드 시작 판정 ---
        if not note.is_judged and abs(note_head_y - self.judgement_line_y) <= self.thresholds['GREAT']:
            note.is_judged = True
            if note.target_pose == current_pose:
                distance = abs(note_head_y - self.judgement_line_y)
                judgement = 'PERFECT' if distance <= self.thresholds['PERFECT'] else 'GREAT'
                note.is_holding = True
            else:
                judgement = 'MISS'
                note.is_failed = True
            
            judgements.append({'judgement': judgement, 'note': note})
            return

        # --- Phase 2 & 3: 홀드 유지 및 종료 판정 ---
        if note.is_holding:
            # 유지 판정 (몸통이 판정선 위에 있을 때)
            if note_tail_y < self.judgement_line_y < note_head_y:
                if note.target_pose != current_pose:
                    note.is_holding = False
                    note.is_failed = True
                    judgements.append({'judgement': 'HOLD_BREAK', 'note': note})
            
            # 종료 판정 (꼬리가 판정선을 지났을 때)
            elif note_tail_y >= self.judgement_line_y:
                note.is_holding = False
                judgements.append({'judgement': 'HOLD_SUCCESS', 'note': note})