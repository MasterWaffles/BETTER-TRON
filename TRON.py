import pygame
import sys
import json
import random
from enum import Enum
from time import time


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

#BASICALLY EVERYTHING
class LightCycle:
    def __init__(self, x, y, color, direction, key_controls, player_name, speed, is_ai=False):
        self.x = x
        self.y = y
        self.color = color
        self.direction = direction
        self.trail = [(x, y, time())]
        self.key_controls = key_controls
        self.player_name = player_name
        self.speed = speed
        self.alive = True
        self.is_ai = is_ai
        self.player_directions = []
        #MOVEMENTS
    def move(self):
        if not self.alive:
            return
        dx, dy = self.direction.value
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.trail.append((self.x, self.y, time()))

    def change_direction(self, new_direction):
        if not self.alive:
            return
        current_dx, current_dy = self.direction.value
        new_dx, new_dy = new_direction.value
        if (current_dx, current_dy) != (-new_dx, -new_dy):
            self.direction = new_direction
        #BOT MLVEMENTS
    def ai_move(self, other_trail, screen_width, screen_height, difficulty, player_directions):
        if not self.alive or not self.is_ai:
            return

        possible_directions = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        safe_directions = []
        current_dx, current_dy = self.direction.value

        for direction in possible_directions:
            dx, dy = direction.value
            if (dx, dy) == (-current_dx, -dy):
                continue
            new_x = self.x + dx * self.speed * 10
            new_y = self.y + dy * self.speed * 10
            if (new_x >= 10 and new_x <= screen_width - 10 and
                    new_y >= 10 and new_y <= screen_height - 10):
                safe = True
                recent_trail = other_trail[-200:] if len(other_trail) > 200 else other_trail
                for segment in recent_trail + self.trail[-200:-10]:
                    if abs(new_x - segment[0]) < 15 and abs(new_y - segment[1]) < 15:
                        safe = False
                        break
                if safe:
                    safe_directions.append(direction)

        if safe_directions:
            if difficulty == "hard":
                best_direction = self.choose_best_direction(
                    safe_directions, other_trail, screen_width, screen_height, player_directions)
                self.change_direction(best_direction)
            elif difficulty == "medium":
                self.change_direction(random.choice(safe_directions))
            else:
                if random.random() < 0.3:
                    self.change_direction(random.choice(safe_directions))
        elif difficulty != "easy":
            self.change_direction(random.choice(possible_directions))

    def choose_best_direction(self, safe_directions, other_trail, screen_width, screen_height, player_directions):
        best_direction = safe_directions[0]
        max_space = -1

        recent_trail = other_trail[-200:] if len(other_trail) > 200 else other_trail
        for direction in safe_directions:
            dx, dy = direction.value
            steps = 0
            x, y = self.x, self.y
            score = 0
            if player_directions:
                player_dx, player_dy = player_directions[-1].value
                if (dx, dy) == (player_dx, player_dy):
                    score += 10
                elif (dx, dy) == (-player_dx, -player_dy):
                    score -= 5
            while (x >= 10 and x <= screen_width - 10 and
                   y >= 10 and y <= screen_height - 10):
                x += dx * self.speed
                y += dy * self.speed
                steps += 1
                for segment in recent_trail + self.trail[-200:-10]:
                    if abs(x - segment[0]) < 15 and abs(y - segment[1]) < 15:
                        steps -= 1
                        break
                else:
                    continue
                break
            total_score = steps + score
            if total_score > max_space:
                max_space = total_score
                best_direction = direction

        return best_direction

    def draw(self, screen):
        if not self.alive:
            return
        surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        for i in range(len(self.trail) - 1):
            pygame.draw.line(surface, self.color,
                             (self.trail[i][0], self.trail[i][1]),
                             (self.trail[i + 1][0], self.trail[i + 1][1]), 3)
        screen.blit(surface, (0, 0))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 5)
            ##CRASH PHYSICS
    def check_collision(self, other_trail, screen_width, screen_height):
        if not self.alive:
            return False
        head = (self.x, self.y)
        if (self.x < 10 or self.x > screen_width - 10 or
                self.y < 10 or self.y > screen_height - 10):
            self.alive = False
            return True
        recent_trail = other_trail[-200:] if len(other_trail) > 200 else other_trail
        for segment in recent_trail + self.trail[-200:-10]:
            if abs(self.x - segment[0]) < 5 and abs(self.y - segment[1]) < 5:
                self.alive = False
                return True
        return False


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen_info = pygame.display.Info()
        self.screen_width = self.screen_info.current_w
        self.screen_height = self.screen_info.current_h
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), pygame.FULLSCREEN)
        pygame.display.set_caption("Tron Light Cycle")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 72)
        self.state = "home"
        self.paused = False
        self.countdown = None

        self.player1_controls = {
            pygame.K_w: Direction.UP,
            pygame.K_s: Direction.DOWN,
            pygame.K_a: Direction.LEFT,
            pygame.K_d: Direction.RIGHT
        }
        self.player2_controls = {
            pygame.K_UP: Direction.UP,
            pygame.K_DOWN: Direction.DOWN,
            pygame.K_LEFT: Direction.LEFT,
            pygame.K_RIGHT: Direction.RIGHT
        }

        try:
            self.collision_sound = pygame.mixer.Sound("collision.wav")
        except:
            self.collision_sound = None
        try:
            self.victory_sound = pygame.mixer.Sound("victory.wav")
        except:
            self.victory_sound = None

        self.load_settings()
        self.cycle1 = None
        self.cycle2 = None
        self.game_over = False
        self.winner = None
        self.in_settings = False
        self.single_player = False

        self.color_options = [
            (0, 255, 255),
            (255, 255, 0),
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255)
        ]
        self.speed_options = [5, 10, 15, 20]
        self.difficulty_options = ["easy", "medium", "hard"]

        self.settings_button_rect = pygame.Rect(self.screen_width - 150, 20, 100, 50)
        self.exit_settings_rect = pygame.Rect(
            self.screen_width // 2 - 150, self.screen_height - 150, 300, 80)
        self.single_player_rect = pygame.Rect(
            self.screen_width // 2 - 150, self.screen_height // 2 - 100, 300, 100)
        self.multiplayer_rect = pygame.Rect(
            self.screen_width // 2 - 150, self.screen_height // 2 + 50, 300, 100)
        self.pause_resume_rect = pygame.Rect(
            self.screen_width // 2 - 150, self.screen_height // 2 - 100, 300, 80)
        self.pause_restart_rect = pygame.Rect(
            self.screen_width // 2 - 150, self.screen_height // 2, 300, 80)
        self.pause_home_rect = pygame.Rect(
            self.screen_width // 2 - 150, self.screen_height // 2 + 100, 300, 80)

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
                self.p1_color = tuple(settings["p1_color"])
                self.p2_color = tuple(settings["p2_color"])
                self.speed = settings["speed"]
                self.difficulty = settings.get("difficulty", "medium")
        except:
            self.p1_color = (0, 255, 255)
            self.p2_color = (255, 255, 0)
            self.speed = 10
            self.difficulty = "medium"

    def save_settings(self):
        settings = {
            "p1_color": list(self.cycle1.color) if self.cycle1 else list(self.p1_color),
            "p2_color": list(self.cycle2.color) if self.cycle2 else list(self.p2_color),
            "speed": self.speed,
            "difficulty": self.difficulty
        }
        with open("settings.json", "w") as f:
            json.dump(settings, f)

    def init_game(self, single_player):
        self.single_player = single_player
        self.cycle1 = LightCycle(
            self.screen_width // 4, self.screen_height // 2,
            self.p1_color, Direction.RIGHT, self.player1_controls,
            "Player 1", self.speed)
        self.cycle2 = LightCycle(
            3 * self.screen_width // 4, self.screen_height // 2,
            self.p2_color, Direction.LEFT,
            self.player2_controls if not single_player else {},
            "AI" if single_player else "Player 2", self.speed, is_ai=single_player)
        self.game_over = False
        self.winner = None
        self.in_settings = False
        self.paused = False
        self.countdown = time()
        self.state = "game"

    def reset_game(self):
        self.cycle1 = None
        self.cycle2 = None
        self.game_over = False
        self.winner = None
        self.in_settings = False
        self.paused = False
        self.countdown = None
        self.state = "home"

    def handle_keyboard_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.save_settings()
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.state == "game" and not self.in_settings and not self.paused and self.countdown is None:
                    if event.key in self.cycle1.key_controls and self.cycle1.alive:
                        self.cycle1.change_direction(self.cycle1.key_controls[event.key])
                    if (not self.single_player and
                            event.key in self.cycle2.key_controls and self.cycle2.alive):
                        self.cycle2.change_direction(self.cycle2.key_controls[event.key])
                    if event.key == pygame.K_SPACE and self.game_over:
                        self.save_settings()
                        self.reset_game()
                if event.key == pygame.K_ESCAPE:
                    if self.state == "game" and not self.game_over and not self.in_settings:
                        self.paused = not self.paused
                    elif self.paused:
                        self.paused = False

    def handle_mouse_input(self):
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:
            mouse_pos = pygame.mouse.get_pos()

            if self.state == "home":
                if self.single_player_rect.collidepoint(mouse_pos):
                    self.init_game(True)
                elif self.multiplayer_rect.collidepoint(mouse_pos):
                    self.init_game(False)

            elif self.state == "game":
                if self.game_over:
                    restart_rect = pygame.Rect(
                        self.screen_width // 2 - 150, self.screen_height // 2 + 50, 300, 100)
                    if restart_rect.collidepoint(mouse_pos):
                        self.save_settings()
                        self.reset_game()

                elif self.paused:
                    if self.pause_resume_rect.collidepoint(mouse_pos):
                        self.paused = False
                    elif self.pause_restart_rect.collidepoint(mouse_pos):
                        self.init_game(self.single_player)
                    elif self.pause_home_rect.collidepoint(mouse_pos):
                        self.save_settings()
                        self.reset_game()

                elif self.in_settings:
                    for i, color in enumerate(self.color_options):
                        p1_rect = pygame.Rect(
                            self.screen_width // 4 - 50,
                            self.screen_height // 2 - 50 + i * 60, 100, 50)
                        p2_rect = pygame.Rect(
                            3 * self.screen_width // 4 - 50,
                            self.screen_height // 2 - 50 + i * 60, 100, 50)
                        if p1_rect.collidepoint(mouse_pos) and color != self.cycle2.color:
                            self.cycle1.color = color
                        if p2_rect.collidepoint(mouse_pos) and color != self.cycle1.color:
                            self.cycle2.color = color

                    for i, speed in enumerate(self.speed_options):
                        speed_rect = pygame.Rect(
                            self.screen_width // 2 - 100,
                            self.screen_height // 2 - 50 + i * 60, 100, 50)
                        if speed_rect.collidepoint(mouse_pos):
                            self.speed = speed
                            self.cycle1.speed = speed
                            self.cycle2.speed = speed

                    for i, difficulty in enumerate(self.difficulty_options):
                        diff_rect = pygame.Rect(
                            self.screen_width // 2 + 50,
                            self.screen_height // 2 - 50 + i * 60, 100, 50)
                        if diff_rect.collidepoint(mouse_pos) and self.single_player:
                            self.difficulty = difficulty

                    if self.exit_settings_rect.collidepoint(mouse_pos):
                        self.save_settings()
                        self.in_settings = False

                else:
                    if self.settings_button_rect.collidepoint(mouse_pos):
                        self.in_settings = True

    def update(self):
        if self.state != "game" or self.game_over or self.in_settings or self.paused or self.countdown is not None:
            return

        self.cycle1.move()
        self.cycle2.move()

        if self.single_player:
            self.cycle2.ai_move(
                self.cycle1.trail, self.screen_width, self.screen_height,
                self.difficulty, self.cycle1.player_directions)

        if (self.cycle1.check_collision(self.cycle2.trail, self.screen_width, self.screen_height) or
                self.cycle2.check_collision(self.cycle1.trail, self.screen_width, self.screen_height)):
            if self.collision_sound:
                self.collision_sound.play()
            self.game_over = True
            if not self.cycle1.alive and not self.cycle2.alive:
                self.winner = "Draw"
            elif not self.cycle1.alive:
                self.winner = self.cycle2.player_name
            else:
                self.winner = self.cycle1.player_name
            if self.victory_sound:
                self.victory_sound.play()

    def draw(self):
        self.screen.fill((0, 0, 0))

        if self.state == "home":
            title_text = self.font.render("Tron Light Cycle", True, (255, 255, 255))
            single_text = self.font.render("Single Player", True, (255, 255, 255))
            multi_text = self.font.render("Multiplayer", True, (255, 255, 255))

            self.screen.blit(
                title_text,
                (self.screen_width // 2 - title_text.get_width() // 2, self.screen_height // 2 - 250))
            self.screen.blit(
                single_text,
                (self.screen_width // 2 - single_text.get_width() // 2, self.screen_height // 2 - 90))
            self.screen.blit(
                multi_text,
                (self.screen_width // 2 - multi_text.get_width() // 2, self.screen_height // 2 + 60))

        elif self.state == "game":
            pygame.draw.rect(
                self.screen, (255, 0, 0),
                (0, 0, self.screen_width, self.screen_height), 10)

            if not self.in_settings and not self.paused:
                self.cycle1.draw(self.screen)
                self.cycle2.draw(self.screen)

                settings_text = self.font.render("Menu", True, (255, 255, 255))
                self.screen.blit(settings_text, (self.screen_width - 140, 20))

                if self.countdown is not None:
                    elapsed = time() - self.countdown
                    if elapsed < 1:
                        text = self.font.render("3", True, (255, 255, 255))
                    elif elapsed < 2:
                        text = self.font.render("2", True, (255, 255, 255))
                    elif elapsed < 3:
                        text = self.font.render("1", True, (255, 255, 255))
                    elif elapsed < 4:
                        text = self.font.render("GO!", True, (255, 255, 255))
                    else:
                        self.countdown = None
                        text = None
                    if text:
                        self.screen.blit(
                            text,
                            (self.screen_width // 2 - text.get_width() // 2, self.screen_height // 2))

                if self.game_over:
                    game_over_text = self.font.render(
                        f"Game Over! {self.winner} Wins!", True, (255, 255, 255))
                    restart_text = self.font.render("Back to Home", True, (255, 255, 255))
                    self.screen.blit(
                        game_over_text,
                        (self.screen_width // 2 - game_over_text.get_width() // 2,
                         self.screen_height // 2 - 50))
                    self.screen.blit(
                        restart_text,
                        (self.screen_width // 2 - restart_text.get_width() // 2,
                         self.screen_height // 2 + 50))

            elif self.paused:
                pause_text = self.font.render("Paused", True, (255, 255, 255))
                resume_text = self.font.render("Resume", True, (255, 255, 255))
                restart_text = self.font.render("Restart", True, (255, 255, 255))
                home_text = self.font.render("Back to Home", True, (255, 255, 255))

                self.screen.blit(
                    pause_text,
                    (self.screen_width // 2 - pause_text.get_width() // 2, self.screen_height // 2 - 200))
                self.screen.blit(
                    resume_text,
                    (self.screen_width // 2 - resume_text.get_width() // 2, self.screen_height // 2 - 90))
                self.screen.blit(
                    restart_text,
                    (self.screen_width // 2 - restart_text.get_width() // 2, self.screen_height // 2 + 10))
                self.screen.blit(
                    home_text,
                    (self.screen_width // 2 - home_text.get_width() // 2, self.screen_height // 2 + 110))

            else:
                p1_label = self.font.render("Player 1 Colors", True, (255, 255, 255))
                p2_label = self.font.render(
                    f"{'AI' if self.single_player else 'Player 2'} Colors", True, (255, 255, 255))
                speed_label = self.font.render("Speed", True, (255, 255, 255))
                diff_label = self.font.render(
                    "AI Difficulty", True, (255, 255, 255)) if self.single_player else self.font.render(
                    "", True, (255, 255, 255))

                self.screen.blit(
                    p1_label,
                    (self.screen_width // 4 - p1_label.get_width() // 2, self.screen_height // 2 - 150))
                self.screen.blit(
                    p2_label,
                    (3 * self.screen_width // 4 - p2_label.get_width() // 2, self.screen_height // 2 - 150))
                self.screen.blit(
                    speed_label,
                    (self.screen_width // 2 - 100 - speed_label.get_width() // 2, self.screen_height // 2 - 150))
                self.screen.blit(
                    diff_label,
                    (self.screen_width // 2 + 50 - diff_label.get_width() // 2, self.screen_height // 2 - 150))

                for i, color in enumerate(self.color_options):
                    pygame.draw.rect(
                        self.screen, color,
                        (self.screen_width // 4 - 50, self.screen_height // 2 - 50 + i * 60, 100, 50))
                    pygame.draw.rect(
                        self.screen, color,
                        (3 * self.screen_width // 4 - 50, self.screen_height // 2 - 50 + i * 60, 100, 50))

                for i, speed in enumerate(self.speed_options):
                    speed_text = self.font.render(str(speed), True, (255, 255, 255))
                    self.screen.blit(
                        speed_text,
                        (self.screen_width // 2 - 100 + 50 - speed_text.get_width() // 2,
                         self.screen_height // 2 - 50 + i * 60 + 10))

                if self.single_player:
                    for i, difficulty in enumerate(self.difficulty_options):
                        diff_text = self.font.render(difficulty.capitalize(), True, (255, 255, 255))
                        self.screen.blit(
                            diff_text,
                            (self.screen_width // 2 + 50 + 50 - diff_text.get_width() // 2,
                             self.screen_height // 2 - 50 + i * 60 + 10))

                exit_text = self.font.render("Exit Settings", True, (255, 255, 255))
                self.screen.blit(
                    exit_text,
                    (self.screen_width // 2 - exit_text.get_width() // 2, self.screen_height - 140))

        pygame.display.flip()

    def run(self):
        while True:
            self.handle_keyboard_input()
            self.handle_mouse_input()
            self.update()
            self.draw()
            self.clock.tick(60)


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()