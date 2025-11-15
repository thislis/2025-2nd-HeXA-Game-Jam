# judgement_engine.py
# 이 파일의 내용을 아래 코드로 전체 교체하세요.

class JudgementEngine:
    def __init__(self, line_y, thresholds, note_speed, swipe_params, note_radius):
        self.judgement_line_y = line_y
        self.thresholds = thresholds
        self.note_speed = note_speed
        self.swipe_distance = swipe_params['distance']
        self.swipe_pos_tolerance = swipe_params['tolerance']
        self.swipe_pose_grace_period = swipe_params['grace_period']
        self.note_radius = note_radius

    def check_judgements(self, notes, current_pose, hand_pos, game_time, delta_time):
        judgements = []
        for note in notes:
            if note.is_failed: continue

            if note.note_type == 'tap':
                if not note.is_judged: self._judge_tap_note(note, current_pose, judgements)
            elif note.note_type == 'hold':
                self._judge_hold_note(note, current_pose, judgements)
            elif note.note_type == 'swipe':
                self._judge_swipe_note(note, current_pose, hand_pos, game_time, delta_time, judgements)

            # <<< 핵심 변경 부분: 자동 MISS 판정 조건을 훨씬 너그럽게 변경
            # 이전: 노트 아랫부분이 GREAT 존을 벗어났을 때
            # 변경: 노트 윗부분이 판정선을 완전히 지나갔을 때
            if not note.is_judged and (note.y_pos - self.note_radius) > self.judgement_line_y:
                note.is_judged = True
                note.is_failed = True
                judgements.append({'judgement': 'MISS', 'note': note})
        
        return judgements

    # 이하 _judge_... 메소드들은 이전 버전과 동일합니다.
    def _judge_tap_note(self, note, current_pose, judgements):
        note_bottom_y = note.y_pos + self.note_radius
        distance = abs(note_bottom_y - self.judgement_line_y)
        if distance <= self.thresholds['GREAT']:
            note.is_judged = True
            if note.target_pose == current_pose:
                judgement = 'PERFECT' if distance <= self.thresholds['PERFECT'] else 'GREAT'
            else:
                judgement = 'MISS'; note.is_failed = True
            judgements.append({'judgement': judgement, 'note': note})

    def _judge_hold_note(self, note, current_pose, judgements):
        note_head_bottom_y = note.y_pos + self.note_radius
        distance = abs(note_head_bottom_y - self.judgement_line_y)
        hold_length_pixels = note.duration * self.note_speed
        note_tail_y = note.y_pos - hold_length_pixels
        if not note.is_judged and distance <= self.thresholds['GREAT']:
            note.is_judged = True
            if note.target_pose == current_pose:
                judgement = 'PERFECT' if distance <= self.thresholds['PERFECT'] else 'GREAT'
                note.is_holding = True
            else:
                judgement = 'MISS'; note.is_failed = True
            judgements.append({'judgement': judgement, 'note': note}); return
        if note.is_holding:
            if note_tail_y < self.judgement_line_y < note.y_pos and note.target_pose != current_pose:
                note.is_holding = False; note.is_failed = True
                judgements.append({'judgement': 'HOLD_BREAK', 'note': note})
            elif note_tail_y >= self.judgement_line_y:
                note.is_holding = False
                judgements.append({'judgement': 'HOLD_SUCCESS', 'note': note})

    def _judge_swipe_note(self, note, current_pose, hand_pos, game_time, delta_time, judgements):
        start_x = 800 // 2
        target_x = start_x + self.swipe_distance if note.direction == "RIGHT" else start_x - self.swipe_distance
        if not note.is_judged and abs(note.y_pos - self.judgement_line_y) <= self.thresholds['GREAT']:
            note.is_judged = True
            hand_x = hand_pos[0] if hand_pos else 0
            pose_ok = note.target_pose == current_pose
            pos_ok = abs(hand_x - start_x) <= self.swipe_pos_tolerance
            if pose_ok and pos_ok:
                distance = abs(note.y_pos - self.judgement_line_y)
                judgement = 'PERFECT' if distance <= self.thresholds['PERFECT'] else 'GREAT'
                note.is_swiping = True
                note.swipe_end_time = game_time + note.duration
                note.swipe_pose_grace_timer = self.swipe_pose_grace_period
            else:
                judgement = 'MISS'; note.is_failed = True
            judgements.append({'judgement': judgement, 'note': note}); return
        if note.is_swiping:
            if note.target_pose == current_pose:
                note.swipe_pose_grace_timer = self.swipe_pose_grace_period
            else:
                note.swipe_pose_grace_timer -= delta_time
                if note.swipe_pose_grace_timer <= 0:
                    note.is_swiping = False; note.is_failed = True
                    judgements.append({'judgement': 'SWIPE_BREAK', 'note': note}); return
            if game_time >= note.swipe_end_time:
                note.is_swiping = False
                hand_x = hand_pos[0] if hand_pos else 0
                if abs(hand_x - target_x) <= self.swipe_pos_tolerance:
                    judgements.append({'judgement': 'SWIPE_SUCCESS', 'note': note})
                else:
                    note.is_failed = True
                    judgements.append({'judgement': 'SWIPE_BREAK', 'note': note})