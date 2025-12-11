from  typing import *

import textwrap
from tangl.31.utils.jinja_filters import *
from tangl.31.actor.actor_properties import Gens as G

# ------------------------
# TEXT TEMPLATING HELPERS
# ------------------------


class PersonTextMixin(object):

    @property
    def she(self: 'Person') -> str:
        return self.working_gender == G.XY and "he" or "she"
    he = she
    @property
    def She(self: 'Person') -> str:
        return self.working_gender == G.XY and "He" or "She"
    He = She

    @property
    # her_/his_ thing
    def her_(self: 'Person') -> str:
        return self.working_gender == G.XY and "his" or "her"
    his_ = her_
    @property
    def Her_(self: 'Person') -> str:
        return self.working_gender == G.XY and "His" or "Her"
    His_ = Her_

    @property
    # gave to her
    def _her(self: typ.Union['Person', "PersonTextMixin"]) -> str:
        return self.working_gender == G.XY and "him" or "her"
    him = _her

    @property
    # did it to herself
    def herself(self: typ.Union['Person', "PersonTextMixin"]) -> str:
        return self.working_gender == G.XY and "himself" or "herself"
    himself = herself

    @property
    # The thing is hers/his
    def hers(self: typ.Union['Person', "PersonTextMixin"]) -> str:
        return self.working_gender == G.XY and "his" or "hers"
    _his = hers

    @property
    def reproductive_organs(self: typ.Union['Person', "PersonTextMixin"]):
        if self.has_xy >= 30 and self.has_xx >= 30:
            return "has a working penis and testicles and a vagina and womb"
        elif self.has_xy >= 30:
            return "has a working penis and testicles"
        elif self.has_xy > 0:
            return "has a penis, but has been castrated"
        elif self.has_xx >= 30:
            return "has a vagina and womb"
        else:
            return "is a null"

    @property
    def breast_sz(self: typ.Union['Person', "PersonTextMixin"]):
        if self.breasts < 10:
            return "no breasts"
        elif self.breasts < 30:
            return "minimal breasts"
        elif self.breasts < 50:
            return "breasts"
        elif self.breasts < 70:
            return "large breasts"
        else:
            return "gross milky udders"

    @property
    def compliant(self: typ.Union['Person', "PersonTextMixin"]):
        if self.obedience > 50:
            return f"{OBEDIENT}compliant{END_S}"
        if self.obedience > 50:
            return f"{DISOBEDIENT}disobedient{END_S}"
        else:
            return f"{DISOBEDIENT}defiant{END_S}"
    defiant = compliant

    @property
    def phealthy(self: typ.Union['Person', "PersonTextMixin"]):
        if self.phealth > 50:
            return f"{HEALTHY}healthy{END_S}"
        elif self.phealth > 50:
            return f"{UNHEALTHY}unhealthy{END_S}"
        else:
            return f"{UNHEALTHY}near-death{END_S}"

    @property
    def mhealthy(self: typ.Union['Person', "PersonTextMixin"]):
        if self.mhealth > 50:
            return f"{HEALTHY}competent{END_S}"
        elif self.mhealth > 0:
            return f"{UNHEALTHY}nervous{END_S}"
        else:
            return f"{UNHEALTHY}mindbroken{END_S}"

    # TODO: Should be ave_height given gender?
    @property
    def tall(self: typ.Union['Person', "PersonTextMixin"]):
        if self.height > self.ave_height * 1.2:
            return "tall"
        elif self.height < self.ave_height * 0.8:
            return "petite"
        else:
            return "average height"
    short = tall

    @property
    def feminine(self: typ.Union['Person', "PersonTextMixin"]):
        if self.face_type < 30:
            return "masculine"
        elif self.face_type < 60:
            return "androgynous"
        else:
            return "feminine"

    @property
    def body_type(self: typ.Union['Person', "PersonTextMixin"]):
        if self.bmi < 10:
            return "emaciated"
        elif self.bmi < 20 and self.strength > 60:
            return "lean"
        elif self.bmi < 20:
            return "thin"
        elif self.bmi < 25:
            return "average"
        elif self.bmi > 25 and self.strength > 60:
            return "thick"
        elif self.bmi < 30:
            return "plump"
        else:
            return "obese"

    @property
    def pretty(self: typ.Union['Person', "PersonTextMixin"]):   # Should get these from the range enum names
        if self.attractiveness < 30:
            return "rather plain"
        elif self.attractiveness > 60:
            return "very pretty"
        else:
            return "average looking"

    @property
    def age_yrs(self: typ.Union['Person', "PersonTextMixin"]):
        return int(self.age / 12)

    def general_desc(self: typ.Union['Person', "PersonTextMixin"]):
        """
        Examples:
          Jane Doe is a compliant, unhealthy, mind-broken asian woman.
          She appears feminine and is extremely unpleasant to look at.
          She is short and has a waif-like physique.

          John Doe is a disobedient, healthy, and competent white man.
          He appears masculine and is quite attractive.
          He is tall and has an average physique.
        """

        s = f"""\
        { self.full_name } is a { self.compliant }, { self.phealthy }, 
        { self.mhealthy } {self.skin_color} { self.working_gender.value }.
        
        { self.She } appears { self.feminine } and is { self.pretty }.
        { self.She } is { self.tall } and has a { self.body_type } physique.
        """
        return s

    def mobility_desc(self: typ.Union['Person', "PersonTextMixin"]):
        """
        Examples:
          The tendons in her calves have been surgically shortened, forcing
          her to crawl.

        If no mobility restrictions this can simply be ignored.
        """
        if self.legs >= 30:
            # s = f"{ self.She } has healthy legs and can walk and run."
            return  # Ignore
        elif self.arms >= 30:
            s = f"{ self.Her_ } legs are injured, so she can only crawl slowly from place to place."
        else:
            s = f"{ self.Her_ } legs and arms are injured, so { self.she} cannot move without assistance."
        return s

    def disabilities_desc(self: typ.Union['Person', "PersonTextMixin"]):
        """
        Examples:
          She is deaf, blind, and mute.

        If no disabilities, this can simply be ignored.
        """
        return ""

    def distinguishing_marks_desc(self: typ.Union['Person', "PersonTextMixin"]):
        """
        Examples:
          He has a house chattel brand on his left thigh.
          ---
          She has a house chattel brand on her left thigh, and also has
          scarring on her left arm and leg from a severe prior injury.

        If no distinguishing marks, this can simply be ignored.
        """
        return ""

    def contract_desc(self: typ.Union['Person', "PersonTextMixin"]):
        # TODO: Include contract type and weeks until expiry
        # TODO: Need a better term than contract for lifetime service
        s = f"""\
        { self.She } is { self.age_yrs } years old, and has a { self.weeks_until_expiry }
        weeks remaining on her contract.
        """
        return s

    def background_desc(self):
        """
        Examples:
          He is originally American and had a previous career as a pipelayer.
          He is somewhat skilled in engineering.  He speaks English fluently.
          ---
          Because she is both mind-broken and physically unable to communicate,
          her origin, any previous career or skills, and her facility with
          any languages are unknown.
        """
        s = f"\
        { self.She } is originally \
        { self.nationality.capitalize() if hasattr(self, 'nationality') else 'from elsewhere' } \
        and had a previous career as a \
        { self.background if hasattr(self, 'background') else 'a flit' }.\
        "
        return s + "\n"

    def biological_desc(self: typ.Union['Person', "PersonTextMixin"]):
        """
        Examples:
          He is biologically male, with intact genitals and minimal breasts.
          ---
          She is biologically female, but she has been sterilized and her
          breasts have been removed.
        """

        s = f"""\
        { self.She } is biologically { self.birth_gender.value }, 
        { self.she } { self.reproductive_organs } and has { self.breast_sz }.
        """
        return s

    # TODO: Need a partial market desc, too.

    def cur_desc(self: typ.Union['Person', "PersonTextMixin"]) -> str:

        s  = self.general_desc()               # Health and ethnic overview
        s += self.mobility_desc()              # Injuries to legs, wings
        s += self.disabilities_desc()          # Missing and non-natural anatomy
        s += self.distinguishing_marks_desc()  # Tattoos, branding, scarring
        s += self.contract_desc()
        s += self.background_desc()            # Career, skills and fluency
        s += self.biological_desc()            # Genitalia, pregnancy, breasts

        if self.adulterated:
            s += self.adulteration_desc()

        s = textwrap.dedent(s)
        return s
