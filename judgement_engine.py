class JudgementEngine:
#노트와 플레이어 입력을 비교하여 판정을 내리는 클래스"""
    def init(self, line_y, thresholds):
        self.judgement_line_y = line_y
        # 판정선과의 거리에 따른 판정 기준 (pixel)
        self.thresholds = thresholds # e.g., {'PERFECT': 30, 'GREAT': 60}


    
def check_judgements(self, notes, current_pose):
    """판정선 근처의 노트를 확인하고 판정 결과를 반환합니다."""
    judgements = []
    
    for note in notes:
        if note.is_judged:
            continue

        distance = abs(note.y_pos - self.judgement_line_y)

        # 판정 범위 내에 들어온 노트 처리
        if distance <= self.thresholds['GREAT']:
            # 포즈가 일치하는가?
            if note.target_pose == current_pose:
                judgement = 'PERFECT' if distance <= self.thresholds['PERFECT'] else 'GREAT'
                note.is_judged = True
                judgements.append({'judgement': judgement, 'note': note})
        
        # 판정선을 지나쳐버린 노트 처리 (MISS)
        elif note.y_pos > self.judgement_line_y + self.thresholds['GREAT']:
            note.is_judged = True
            judgements.append({'judgement': 'MISS', 'note': note})
    
    return judgements

  