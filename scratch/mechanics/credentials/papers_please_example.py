from enum import Enum
import random

# puzzle game
from tangl.mechanics.game.game_handler import GameHandler
from .credential_packet import Credentialed

class PapersPleaseGameHandler(GameHandler):
    game_type = 'papers_please'
    class Choice(Enum):
        ACCEPT = 'accept'
        DENY = 'deny'

    rules: dict              # Current immigration rules
    applicant: Credentialed  # Current applicant's documents

    def handle_action(self, user_move):
        # Compare the applicant's documents to the rules
        if self.check_documents():
            correct_move = self.Choice.ACCEPT
        else:
            correct_move = self.Choice.DENY

        # Update the score based on the user's move
        if user_move == correct_move:
            self.score['user'] += 1
        else:
            self.score['opponent'] += 1  # In this case, the 'opponent' is the game itself

        self.round += 1
        self.check_for_game_over()

        # Generate new rules and a new applicant for the next round
        self.rules = self.generate_rules()
        self.applicant = self.generate_applicant()

    def check_documents(self):
        # Check the applicant's documents against the rules
        # This could involve checking various fields, dates, etc.
        # For simplicity, let's just check if the applicant's nationality is allowed
        return self.applicant['nationality'] in self.rules['allowed_nationalities']

    def generate_rules(self):
        # Generate a new set of immigration rules
        # For simplicity, let's just randomly select some allowed nationalities
        nationalities = ['Arstotzka', 'Kolechia', 'Obristan', 'Antegria', 'Republia', 'Impor']
        allowed_nationalities = random.sample(nationalities, random.randint(1, len(nationalities)))
        return {'allowed_nationalities': allowed_nationalities}

    def generate_applicant(self):
        # Generate a new applicant's documents
        # For simplicity, let's just randomly select a nationality
        nationalities = ['Arstotzka', 'Kolechia', 'Obristan', 'Antegria', 'Republia', 'Impor']
        nationality = random.choice(nationalities)
        return {'nationality': nationality}
