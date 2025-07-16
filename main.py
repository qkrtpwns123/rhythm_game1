import pygame
import sys
import random
from enum import Enum

# Game Settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Color Definitions
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)

class GameState(Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3

class JudgmentType(Enum):
    PERFECT = 0
    GREAT = 1
    GOOD = 2
    BAD = 3
    MISS = 4

class NoteType(Enum):
    NORMAL = 0
    LONG = 1

class Note:
    def __init__(self, lane, y):
        self.lane = lane
        self.y = y
        self.hit = False
        self.type = NoteType.NORMAL
        self.off_screen_time = 0  # 화면 밖으로 나간 시간
        
    def update(self, speed):
        """Move note down"""
        self.y += speed 
        
    def is_in_hit_range(self, judgment_line_y, hit_range=60):
        """Check if note is in hit range"""
        return abs(self.y - judgment_line_y) < hit_range
        
    def get_distance_from_judgment_line(self, judgment_line_y):
        """Get distance from judgment line"""
        return abs(self.y - judgment_line_y)
        
    def is_off_screen(self, screen_height):
        """Check if note is off screen"""
        return self.y > screen_height + 50
    
    def draw(self, screen, lane, note_width=70, note_height=20):
        """Draw normal note"""
        rect = pygame.Rect(lane.center_x - note_width//2, 
                         int(self.y) - note_height//2, 
                         note_width, note_height)
        
        pygame.draw.rect(screen, lane.color, rect)
        pygame.draw.rect(screen, WHITE, rect, 2)

class LongNote(Note):
    def __init__(self, lane, y, length):
        super().__init__(lane, y)
        self.type = NoteType.LONG
        self.length = length
        self.holding = False
        self.hold_start_time = 0
        
    def start_hold(self):
        """Start holding the long note"""
        self.holding = True
        self.hold_start_time = pygame.time.get_ticks()
        
    def release_hold(self):
        """Release the long note hold"""
        was_holding = self.holding
        self.holding = False
        return was_holding
        
    def update(self, speed):
        """Update long note (shrink if holding, move if not)"""
        if self.holding:
            # 홀드 중일 때는 길이를 줄이면서 헤드 위치는 고정
            shrink_speed = speed * 1  # 일반 노트 속도와 동일하게 설정
            self.length = max(0, self.length - shrink_speed)
            # 헤드(self.y)는 판정선에 고정, 테일만 아래로 이동하는 효과
        else:
            super().update(speed)
        
    def get_head_y(self):
        """Get head (start) position of long note - 헤드는 아래쪽(판정선 근처)"""
        return self.y   
        
    def get_tail_y(self):
        """Get tail (end) position of long note - 테일은 위쪽"""
        return self.y - self.length
        
    def is_head_in_hit_range(self, judgment_line_y, hit_range=60):
        """Check if head is in hit range"""
        return abs(self.get_head_y() - judgment_line_y) < hit_range
        
    def get_head_distance_from_judgment_line(self, judgment_line_y):
        """Get head distance from judgment line"""
        return abs(self.get_head_y() - judgment_line_y)
        
    def draw(self, screen, lane, note_width=70, note_height=20):
        """Draw long note"""
        # Long note body (테일에서 헤드까지)
        long_rect = pygame.Rect(lane.center_x - note_width//2, 
                              int(self.get_tail_y()), 
                              note_width, self.length)
        pygame.draw.rect(screen, lane.color, long_rect)
        pygame.draw.rect(screen, WHITE, long_rect, 2)
        
        # Head (start part) - 아래쪽 (판정선 근처)
        head_rect = pygame.Rect(lane.center_x - note_width//2, 
                              int(self.get_head_y()) - note_height//2, 
                              note_width, note_height)
        pygame.draw.rect(screen, WHITE, head_rect)
        pygame.draw.rect(screen, lane.color, head_rect, 3)
        
        # Tail (end part) - 위쪽
        tail_rect = pygame.Rect(lane.center_x - note_width//2, 
                              int(self.get_tail_y()) - note_height//2, 
                              note_width, note_height)
        pygame.draw.rect(screen, WHITE, tail_rect)
        pygame.draw.rect(screen, lane.color, tail_rect, 3)
        
        # Highlight if holding
        if self.holding:
            pygame.draw.rect(screen, YELLOW, long_rect, 3)
            pygame.draw.rect(screen, YELLOW, head_rect, 3)

class Lane:
    def __init__(self, center_x, width, color):
        self.center_x = center_x
        self.width = width
        self.color = color
        self.is_pressed = False
        
    def get_left_boundary(self):
        return self.center_x - self.width // 2
        
    def get_right_boundary(self):
        return self.center_x + self.width // 2

class ScoreManager:
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        
    def add_score(self, judgment_type):
        """Add score based on judgment"""
        score_values = {
            JudgmentType.PERFECT: 300,
            JudgmentType.GREAT: 200,
            JudgmentType.GOOD: 100,
            JudgmentType.BAD: 50,
            JudgmentType.MISS: 0
        }
        
        self.score += score_values[judgment_type]
        
        if judgment_type != JudgmentType.MISS and judgment_type != JudgmentType.BAD:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
        else:
            self.combo = 0
            
    def reset(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0

class JudgmentDisplay:
    def __init__(self):
        self.text = ""
        self.color = WHITE
        self.timer = 0
        
    def show_judgment(self, judgment_type):
        """Show judgment text"""
        judgment_info = {
            JudgmentType.PERFECT: ("PERFECT", YELLOW),
            JudgmentType.GREAT: ("GREAT", GREEN),
            JudgmentType.GOOD: ("GOOD", BLUE),
            JudgmentType.BAD: ("BAD", RED),
            JudgmentType.MISS: ("MISS", RED)
        }
        
        self.text, self.color = judgment_info[judgment_type]
        self.timer = 30  # Show for 30 frames
        
    def update(self):
        """Update timer"""
        if self.timer > 0:
            self.timer -= 1
            
    def should_display(self):
        """Check if should display"""
        return self.timer > 0

class RhythmGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Rhythm Game")
        self.clock = pygame.time.Clock()
        
        self.state = GameState.MENU
        self.note_speed = 5
        self.judgment_line_y = SCREEN_HEIGHT - 100
        
        # Game components
        self.score_manager = ScoreManager()
        self.judgment_display = JudgmentDisplay()
        self.notes = []
        
        # Setup lanes
        self.setup_lanes()
        
        # Key states
        self.keys_held = [False, False, False, False]
        
        # Music
        self.music_loaded = False
        self.music_playing = False
        self.game_start_time = 0
        
        self.running = True
        
    def setup_lanes(self):
        """Initialize lanes"""
        lane_colors = [RED, GREEN, BLUE, YELLOW]
        lane_width = 80
        lane_spacing = SCREEN_WIDTH // 5
        
        self.lanes = []
        for i in range(4):
            center_x = lane_spacing * (i + 1)
            self.lanes.append(Lane(center_x, lane_width, lane_colors[i]))
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    if event.key == pygame.K_SPACE:
                        self.start_game()
                elif self.state == GameState.PLAYING:
                    self.handle_key_down(event.key)
            elif event.type == pygame.KEYUP:
                if self.state == GameState.PLAYING:
                    self.handle_key_up(event.key)
    
    def handle_key_down(self, key):
        lane_index = self.get_lane_from_key(key)
        if lane_index != -1:
            self.keys_held[lane_index] = True
            self.lanes[lane_index].is_pressed = True
            self.check_note_hit(lane_index)
    
    def handle_key_up(self, key):
        lane_index = self.get_lane_from_key(key)
        if lane_index != -1:
            self.keys_held[lane_index] = False
            self.lanes[lane_index].is_pressed = False
            self.release_long_notes(lane_index)
    
    def get_lane_from_key(self, key):
        key_mapping = {
            pygame.K_a: 0,
            pygame.K_s: 1,
            pygame.K_d: 2,
            pygame.K_f: 3
        }
        return key_mapping.get(key, -1)
    
    def check_note_hit(self, lane_index):
        """Check note hit for the lane"""
        for note in self.notes[:]:
            if note.lane == lane_index and not note.hit:
                if note.type == NoteType.NORMAL:
                    # Normal note judgment
                    if note.is_in_hit_range(self.judgment_line_y):
                        distance = note.get_distance_from_judgment_line(self.judgment_line_y)
                        judgment_type = self.calculate_judgment(distance)
                        
                        self.score_manager.add_score(judgment_type)
                        self.judgment_display.show_judgment(judgment_type)
                        
                        note.hit = True
                        self.notes.remove(note)
                        return
                        
                elif note.type == NoteType.LONG:
                    # Long note head judgment - 헤드가 판정선에 도달했을 때만
                    head_y = note.get_head_y()
                    if abs(head_y - self.judgment_line_y) < 60:
                        distance = abs(head_y - self.judgment_line_y)
                        judgment_type = self.calculate_judgment(distance)
                        
                        # 헤드 판정은 홀드 시작만, 점수는 완료 시에
                        note.hit = True
                        note.start_hold()
                        self.judgment_display.show_judgment(judgment_type)
                        print(f"Long note hold started! Head at: {head_y}, Line at: {self.judgment_line_y}")
                        return
    
    def release_long_notes(self, lane_index):
        """Handle long note release"""
        for note in self.notes[:]:
            if (note.lane == lane_index and 
                note.type == NoteType.LONG and 
                note.holding):
                
                # Check if tail passed judgment line
                tail_y = note.get_tail_y()
                if tail_y >= self.judgment_line_y + 30:
                    # Successfully completed
                    self.score_manager.add_score(JudgmentType.GREAT)
                    self.judgment_display.show_judgment(JudgmentType.GREAT)
                    print("Long note completed successfully!")
                else:
                    # Failed - released too early
                    self.score_manager.add_score(JudgmentType.MISS)
                    self.judgment_display.show_judgment(JudgmentType.MISS)
                    print("Long note failed - released too early!")
                
                self.notes.remove(note)
    
    def calculate_judgment(self, distance):
        """Calculate judgment based on distance"""
        if distance < 15:
            return JudgmentType.PERFECT
        elif distance < 30:
            return JudgmentType.GREAT
        elif distance < 45:
            return JudgmentType.GOOD
        else:
            return JudgmentType.BAD
    
    def start_game(self):
        self.state = GameState.PLAYING
        self.score_manager.reset()
        self.notes = []
        self.keys_held = [False, False, False, False]
        for lane in self.lanes:
            lane.is_pressed = False
        self.load_music()
        self.load_mario_chart()
    
    def load_music(self):
        """Load Super Mario music"""
        try:
            pygame.mixer.music.load("Super Mario.mp3")
            self.music_loaded = True
            print("Music loaded successfully!")
        except pygame.error as e:
            print(f"Could not load music: {e}")
            self.music_loaded = False
    
    def load_mario_chart(self):
        """Load Super Mario themed chart - manually crafted to match the music"""
        self.notes = []
        
        # Super Mario 테마 멜로디에 맞춘 채보
        # 시간 간격을 조정해서 음악과 싱크를 맞춤
        
        # 인트로 부분 (0-4초)
        beat_spacing = 150  # 비트 간격
        current_y = -300
        
        # "Da da da da da da-da!" - 메인 멜로디 시작
        mario_pattern = [
            (0, current_y),
            (0, current_y - beat_spacing),
            (1, current_y - beat_spacing * 1.8),
            (1, current_y - beat_spacing * 2.8),
            (2, current_y - beat_spacing * 3.6),
            (2, current_y - beat_spacing * 4.2),
            (3, current_y - beat_spacing * 4.5),
            
            (0, current_y - beat_spacing * 5),
            (1, current_y - beat_spacing * 5.4),
            (2, current_y - beat_spacing * 5.8),
            (3, current_y - beat_spacing * 6.2),
            (2, current_y - beat_spacing * 6.8),
            (1, current_y - beat_spacing * 7.2),
            (0, current_y - beat_spacing * 7.8),
            (1, current_y - beat_spacing * 8.4),
            (2, current_y - beat_spacing * 8.7),
            (0, current_y - beat_spacing * 9.0),
            
            
        ]
        
        # 패턴을 노트로 변환
        for pattern in mario_pattern:
            lane = pattern[0]
            y_pos = pattern[1]
            
            if len(pattern) == 3:  # 롱노트
                length = pattern[2]
                note = LongNote(lane, y_pos, length)
            else:  # 일반 노트
                note = Note(lane, y_pos)
            
            self.notes.append(note)
        
        # 음악 시작
        if self.music_loaded:
            pygame.mixer.music.play()
            self.music_playing = True
            self.game_start_time = pygame.time.get_ticks()
        
        print(f"Generated {len(self.notes)} Mario-themed notes!")
    
    def update(self):
        if self.state == GameState.PLAYING:
            # Move notes
            for note in self.notes:
                note.update(self.note_speed)
            
            # Check long note completion
            for note in self.notes[:]:
                if (note.type == NoteType.LONG and 
                    note.holding):
                    
                    # 롱노트 길이가 0이 되면 완료
                    if note.length <= 0:
                        if self.keys_held[note.lane]:
                            # 성공적으로 완료
                            self.score_manager.add_score(JudgmentType.GREAT)
                            self.judgment_display.show_judgment(JudgmentType.GREAT)
                            print("Long note completed successfully!")
                        else:
                            # 키를 놓고 있었음
                            self.score_manager.add_score(JudgmentType.MISS)
                            self.judgment_display.show_judgment(JudgmentType.MISS)
                            print("Long note failed - key not held at completion!")
                        self.notes.remove(note)
                        continue
                    
                    # 홀드 중에 키를 놓았는지 확인
                    if not self.keys_held[note.lane]:
                        self.score_manager.add_score(JudgmentType.MISS)
                        self.judgment_display.show_judgment(JudgmentType.MISS)
                        print("Long note failed - key released during hold!")
                        self.notes.remove(note)
            
            # Handle off-screen notes (3 second delay before MISS)
            for note in self.notes[:]:
                if note.type == NoteType.NORMAL:
                    if note.is_off_screen(SCREEN_HEIGHT):
                        if not note.hit:
                            note.off_screen_time += 1
                            # 3초 후 (60 FPS * 3 = 180 frames)
                            if note.off_screen_time >= 180:
                                self.score_manager.add_score(JudgmentType.MISS)
                                self.judgment_display.show_judgment(JudgmentType.MISS)
                                self.notes.remove(note)
                        else:
                            self.notes.remove(note)
                elif note.type == NoteType.LONG:
                    # 롱노트는 테일이 화면을 벗어났을 때
                    if note.get_tail_y() > SCREEN_HEIGHT + 50:
                        if not note.hit:
                            note.off_screen_time += 1
                            # 3초 후 MISS
                            if note.off_screen_time >= 180:
                                self.score_manager.add_score(JudgmentType.MISS)
                                self.judgment_display.show_judgment(JudgmentType.MISS)
                                self.notes.remove(note)
                        else:
                            self.notes.remove(note)
            
            # Update judgment display
            self.judgment_display.update()
    
    def draw(self):
        self.screen.fill(BLACK)
        
        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.PLAYING:
            self.draw_game()
        
        pygame.display.flip()
    
    def draw_menu(self):
        font = pygame.font.Font(None, 74)
        title = font.render("Rhythm Game", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
        self.screen.blit(title, title_rect)
        
        font_small = pygame.font.Font(None, 36)
        start_text = font_small.render("Press SPACE to start", True, WHITE)
        start_rect = start_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        self.screen.blit(start_text, start_rect)
        
        controls = font_small.render("Controls: A, S, D, F", True, WHITE)
        controls_rect = controls.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 100))
        self.screen.blit(controls, controls_rect)
    
    def draw_game(self):
        # Draw lanes
        self.draw_lanes()
        
        # Draw judgment line
        pygame.draw.line(self.screen, RED, (0, self.judgment_line_y), 
                        (SCREEN_WIDTH, self.judgment_line_y), 4)
        
        # Draw notes
        self.draw_notes()
        
        # Draw UI
        self.draw_ui()
        
        # Draw judgment
        self.draw_judgment()
    
    def draw_lanes(self):
        """Draw lanes"""
        for lane in self.lanes:
            left_x = lane.get_left_boundary()
            right_x = lane.get_right_boundary()
            
            # Lane boundaries
            pygame.draw.line(self.screen, WHITE, (left_x, 0), (left_x, SCREEN_HEIGHT), 2)
            pygame.draw.line(self.screen, WHITE, (right_x, 0), (right_x, SCREEN_HEIGHT), 2)
            
            # Highlight if pressed
            if lane.is_pressed:
                highlight_rect = pygame.Rect(left_x, self.judgment_line_y - 30, 
                                           lane.width, 60)
                pygame.draw.rect(self.screen, GRAY, highlight_rect, 0)
    
    def draw_notes(self):
        """Draw notes"""
        for note in self.notes:
            # 화면 밖으로 나가도 계속 그리기 (더 넓은 범위)
            if -500 <= note.y <= SCREEN_HEIGHT + 500:
                lane = self.lanes[note.lane]
                note.draw(self.screen, lane)
    
    def draw_ui(self):
        """Draw UI"""
        font = pygame.font.Font(None, 36)
        
        score_text = font.render(f"Score: {self.score_manager.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        combo_text = font.render(f"Combo: {self.score_manager.combo}", True, WHITE)
        self.screen.blit(combo_text, (10, 50))
        
        max_combo_text = font.render(f"Max Combo: {self.score_manager.max_combo}", True, WHITE)
        self.screen.blit(max_combo_text, (10, 90))
    
    def draw_judgment(self):
        """Draw judgment text"""
        if self.judgment_display.should_display():
            judgment_font = pygame.font.Font(None, 48)
            judgment_surface = judgment_font.render(self.judgment_display.text, True, 
                                                  self.judgment_display.color)
            judgment_rect = judgment_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(judgment_surface, judgment_rect)

if __name__ == "__main__":
    game = RhythmGame()
    game.run()  
