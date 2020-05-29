"""
Implements human behavior/government policy changes.
"""
import datetime
import typing
from orderedset import OrderedSet

import numpy as np

from covid19sim.constants import BIG_NUMBER

if typing.TYPE_CHECKING:
    from covid19sim.simulator import Human
    from covid19sim.base import PersonalMailboxType


class BehaviorInterventions(object):
    """
    A base class to modify behavior based on the type of intervention.
    """
    def __init__(self):
        """
        [summary]
        """
        pass

    def modify_behavior(self, human):
        """
        Changes the behavior attributes of `Human`.
        This function can add new attributes to `Human`.
        If the name of the attribute being changed is `attr`, a new attribute
        is `_attr`.
        `_attr` stores the `attribute` value of `Human` before the change will be made.
        `attr` will store new value.

        Args:
            human (Human): `Human` object.
        """
        pass

    def revert_behavior(self, human):
        """
        Resets the behavior attributes of `Human`.
        It changes `attr` back to what it was before modifying the `attribute`.
        deletes `_attr` from `Human`.

        Args:
            human (Human): `Human` object.
        """
        pass

    def __repr__(self):
        return "BehaviorInterventions"


class StayHome(BehaviorInterventions):
    """
    TODO.
    Not currently being used.
    """
    def __init__(self):
        pass

    def modify_behavior(self, human):
        human._max_misc_per_week = human.max_misc_per_week
        human._max_shop_per_week = human.max_shop_per_week

        human.max_misc_per_week = 1
        human.max_shop_per_week = 1

    def revert_behavior(self, human):
        human.max_misc_per_week = human._max_misc_per_week
        human.max_shop_per_week = human._max_shop_per_week
        delattr(human, "_max_misc_per_week")
        delattr(human, "_max_shop_per_week")

    def __repr__(self):
        return "Stay Home"

class LimitContact (BehaviorInterventions):
    """
    TODO.
    Not currently being used.
    """
    def __init__(self):
        pass

    def modify_behavior(self, human):
        human._maintain_distance = human.maintain_distance
        human._max_misc_per_week = human.max_misc_per_week
        human._max_shop_per_week = human.max_shop_per_week

        human.maintain_distance = human.conf.get("DEFAULT_DISTANCE") + 100 * (human.carefulness - 0.5)
        human.max_misc_per_week = 1
        human.max_shop_per_week = 1

    def revert_behavior(self, human):
        human.maintain_distance = human._maintain_distance
        human.max_misc_per_week = human._max_misc_per_week
        human.max_shop_per_week = human._max_shop_per_week
        delattr(human, "_maintain_distance")
        delattr(human, "_max_misc_per_week")
        delattr(human, "_max_shop_per_week")

    def __repr__(self):
        return "Limit Contact"


class StandApart(BehaviorInterventions):
    """
    `Human` should maintain an extra distance with other people.
    It adds `_maintain_extra_distance_2m` because of the conflict with a same named attribute in
    `SocialDistancing`
    """
    def __init__(self, default_distance=25):
        self.DEFAULT_SOCIAL_DISTANCE = default_distance

    def modify_behavior(self, human):
        # FIXME : Social distancing also has this parameter
        human._maintain_extra_distance_2m = human.maintain_extra_distance
        human.maintain_extra_distance = self.DEFAULT_SOCIAL_DISTANCE + 100 * (human.carefulness - 0.5)

    def revert_behavior(self, human):
        human.maintain_extra_distance = human._maintain_extra_distance_2m
        delattr(human, "_maintain_extra_distance_2m")

    def __repr__(self):
        return "Stand 2M"

class WashHands(BehaviorInterventions):
    """
    Increases `Human.hygeine`.
    This factor is used to decay likelihood of getting infected/infecting others exponentially.
    """

    def __init__(self):
        pass

    def modify_behavior(self, human):
        assert human.carefulness <= 1.
        human._hygiene = human.hygiene
        human.hygiene = human.rng.uniform(human.carefulness, 1)

    def revert_behavior(self, human):
        human.hygiene = human._hygiene
        delattr(human, "_hygiene")

    def __repr__(self):
        return "Wash Hands"

class Quarantine(BehaviorInterventions):
    """
    Implements quarantining for `Human`. Following is included -
        1. work from home (changes `Human.workplace` to `Human.household`)
        2. rest at home (not go out unless)
        3. stay at home unless hospitalized (so there can still be household infections)
        4. go out with a reduce probability of 0.10 to stores/parks/miscs, but every time `Human` goes out
            they do not explore i.e. do not go to more than one location. (reduce RHO and GAMMA)

    Adds an attribute `_quarantine` to be used as a flag.
    """
    _RHO = 0.1
    _GAMMA = 1

    def __init__(self):
        pass

    def modify_behavior(self, human):
        human._workplace = human.workplace
        human.workplace = human.household
        human.rho = self._RHO
        human.gamma = self._GAMMA
        human.rest_at_home = True
        human._quarantine = True
        # print(f"{human} quarantined {human.tracing_method}")

    def revert_behavior(self, human):
        human.workplace = human._workplace
        human.rho = human.conf.get("RHO")
        human.gamma = human.conf.get("GAMMA")
        human.rest_at_home = False
        human._quarantine = False
        delattr(human, "_workplace")

    def __repr__(self):
        return f"Quarantine"

# FIXME: Lockdown should be a mix of CityBasedIntervention and BehaviorInterventions.
class Lockdown(BehaviorInterventions):
    """
    Implements lockdown. Needs some more work.
    It only implements behvior modification for `Human`. Ideally, it should close down stores/parks/etc.

    Following behavior modifications are included -
        1. reducde mobility through RHO and GAMMA. Enables minimal exploration if going out.
            i.e. `Human` revisits the previously visited location with increased probability.
            If `Human` is on a leisure trip, it visits only a few location.
        2. work from home (changes `Human.workplace` to `Human.household`)
    """
    _RHO = 0.1
    _GAMMA = 1

    def modify_behavior(self, human):
        human._workplace = human.workplace
        human.workplace = human.household
        human.rho = self._RHO
        human.gamma = self._GAMMA

    def revert_behavior(self, human):
        human.workplace = human._workplace
        human.rho = human.conf.get("RHO")
        human.gamma = human.conf.get("GAMMA")
        delattr(human, "_workplace")

    def __repr__(self):
        return f"Lockdown"

class SocialDistancing(BehaviorInterventions):
    """
    Implements social distancing. Following is included -
        1. maintain a distance of 200 cms with other people.
        2. Reduce the time of encounter by 0.5 than what one would do without this intervention.
        3. Reduced mobility (using RHO and GAMMA)

    """
    def __init__(self, default_distance=100, time_encounter_reduction_factor=0.5):
        self.DEFAULT_SOCIAL_DISTANCE = default_distance # cm
        self.TIME_ENCOUNTER_REDUCTION_FACTOR = time_encounter_reduction_factor
        self._RHO = 0.2
        self._GAMMA = 0.5

    def modify_behavior(self, human):
        human._maintain_extra_distance = human.maintain_extra_distance
        human._time_encounter_reduction_factor = human.time_encounter_reduction_factor

        human.maintain_extra_distance = self.DEFAULT_SOCIAL_DISTANCE + 100 * (human.carefulness - 0.5)
        human.time_encounter_reduction_factor = self.TIME_ENCOUNTER_REDUCTION_FACTOR
        human.rho = self._RHO
        human.gamma = self._GAMMA

    def revert_behavior(self, human):
        human.maintain_extra_distance = human._maintain_extra_distance
        human.time_encounter_reduction_factor = human._time_encounter_reduction_factor
        human.rho = human.conf.get("RHO")
        human.gamma = human.conf.get("GAMMA")
        delattr(human, "_maintain_extra_distance")
        delattr(human, "_time_encounter_reduction_factor")

    def __repr__(self):
        """
        [summary]
        """
        return f"Social Distancing"

class BinaryTracing(BehaviorInterventions):
    """
    Implements two recommendations for binary tracing.
    There are only two levels, i.e., 0 and 1.
    At the start of this intervention, everyone is initialized with recommendations
    in the level 0.
    """
    def __init__(self):
        super(BinaryTracing, self).__init__()

    def modify_behavior(self, human):
        if human.rec_level == 0:
            recommendations = [WashHands(), StandApart(default_distance=25)]
        else:
            recommendations = [Quarantine()]
        self.revert_behavior(human)
        for rec in recommendations:
            if isinstance(rec, BehaviorInterventions) and human.rng.rand() < human.how_much_I_follow_recommendations:
                rec.modify_behavior(human)
                human.recommendations_to_follow.add(rec)

    def revert_behavior(self, human):
        for rec in human.recommendations_to_follow:
            rec.revert_behavior(human)
        human.recommendations_to_follow = OrderedSet()


class WearMask(BehaviorInterventions):
    """
    `Human` wears a mask according to `Human.wear_mask()`.
    Sets `Human.WEAR_MASK` to True.
    """

    def __init__(self, available=None):
        super(WearMask, self).__init__()
        self.available = available

    def modify_behavior(self, human):
        if self.available is None:
            human.WEAR_MASK = True
            return

        elif self.available > 0:
            human.WEAR_MASK = True
            self.available -= 1

    def revert_behavior(self, human):
        human.WEAR_MASK = False

    def __repr__(self):
        return f"Wear Mask"

def get_recommendations(level):
    """
    Maps recommendation level to a list `BehaviorInterventions`.

    Args:
        level (int): recommendation level.

    Returns:
        list: a list of `BehaviorInterventions`.
    """
    if level == 0:
        return [WashHands(), StandApart(default_distance=25)]
    if level == 1:
        return [WashHands(), StandApart(default_distance=75), WearMask()]
    if level == 2:
        return [WashHands(), SocialDistancing(default_distance=100), WearMask(), 'monitor_symptoms']

    return [WashHands(), SocialDistancing(default_distance=100), WearMask(), 'monitor_symptoms', GetTested("recommendations"), Quarantine()]

class RiskBasedRecommendations(BehaviorInterventions):
    """
    Implements recommendation based behavior modifications.
    The risk level is mapped to a recommendation level. The thresholds to do so are fixed.
    These thresholds are decided using a heuristic, which is outside the scope of this class.
    Each recommendation level is a list of different `BehaviorInterventions`.

    It uses `Human.recommendations_to_follow` to keep a record of various recommendations
    that `Human` is currently following.
    """

    def __init__(self):
        super(RiskBasedRecommendations, self).__init__()

    @staticmethod
    def get_recommendations_level(risk_level, thresholds, max_risk_level):
        """
        Converts the risk level to recommendation level.

        Args:
            risk_level (int): quantized risk level of range 0-15. sent in encounter messages and update messages.
            thresholds (list|tuple): exactly 3 values to convert risk_level to rec_level
            max_risk_level (int): maximum allowed risk_level for sanity check (assert risk_level <= max_risk_level)

        Returns:
            recommendation level (int): App recommendation level which takes on a range of 0-3.
        """
        if risk_level <= thresholds[0]:
            return 0
        elif thresholds[0] < risk_level <= thresholds[1]:
            return 1
        elif thresholds[1] < risk_level <= thresholds[2]:
            return 2
        elif thresholds[2] < risk_level <= max_risk_level:
            return 3
        else:
            raise

    def modify_behavior(self, human):
        # get the list of recommendations I should be following
        recommendations = get_recommendations(human.rec_level)

        # revert all my previous behaviours
        self.revert_behavior(human)

        # apply each behaviour I should be following
        for rec in recommendations:
            if isinstance(rec, BehaviorInterventions) and human.rng.rand() < human.how_much_I_follow_recommendations:
                rec.modify_behavior(human)
                human.recommendations_to_follow.add(rec)

    def revert_behavior(self, human):
        for rec in human.recommendations_to_follow:
            rec.revert_behavior(human)
        human.recommendations_to_follow = OrderedSet()

class GetTested(BehaviorInterventions):
    """
    `Human` should get tested.
    """
    # FIXME: can't be called as a stand alone class. Needs human.recommendations_to_follow to work
    # FIXME: test_recommended should be _test_recommended. Make it a convention that any attribute added here,
    # starts with _
    def __init__(self, source):
        """
        Args:
            source (str): reason behind getting tested e.g. recommendation, diagnosis, etc.
        """
        self.source = source

    def modify_behavior(self, human):
        human.test_recommended  = True
        # send human to the testing center
        human.check_covid_testing_needs()

    def revert_behavior(self, human):
        human.test_recommended  = False

    def __repr__(self):
        return "Get Tested"


class Tracing(object):
    """
    Implements tracing. It relies on categorization of `Human` according to risk_levels.

    This object carries a bunch of flags & is responsible for determining the risk level of humans when
    the transformer is not used for risk level inference. To do so, it will use the targeted human's
    contact book to pull statistics about its recent contacts.

    If the transformer is used, this object becomes fairly useless, and will only be used to apply
    recommended behavior changes.

    The name of this class is probably not the best, feel free to suggest alternatives.

    Attributes:
        risk_model (str): type of tracing to use. The following methods are currently
            available: digital, manual, naive, other, transformer.
        p_contact (float): adds a noise to the tracing procedure, as it is not always possible
            to contact everyone (or remember all contacts) when using manual tracing.
        delay (int): defines whether there should be a delay between the time when someone
            triggers tracing and someone is traced. It is 0 for digital tracing, and 1 for manual.
        app (bool): defines whether an app is required for this tracing. For example, manual
            tracing doesn't use app.
        max_depth (int, optional): The number of hops away from the source to consider while tracing.
            The term `order` is also used for this. Defaults to 1.
        propagate_symptoms (bool, optional): Defines whether tracing is to be triggered when someone
            reports symptoms. Defaults to False.
        propagate_risk (bool, optional): Define whether tracing is to be triggered when someone
            changes their risk level. Defaults to False. Note: this is not to be mixed with
            risk_model="transformer".
        should_modify_behavior (bool, optional): Defines whether behavior should be modified or not
            following the tracing intervention for conunterfactual studies. Defaults to True.

    """
    def __init__(self, conf: dict):
        """
        Initializes the tracing object.

        Args:
            conf (dict): configuration to parse settings from.
        """
        risk_model = conf.get("RISK_MODEL")
        max_depth = conf.get("TRACING_ORDER")
        symptoms = conf.get("TRACE_SYMPTOMS")
        risk = conf.get("TRACE_RISK_UPDATE")
        should_modify_behavior = conf.get("SHOULD_MODIFY_BEHAVIOR"),

        self.risk_model = risk_model
        if risk_model in ['manual', 'digital']:
            self.intervention = BinaryTracing()
        else:
            # risk based
            self.intervention = RiskBasedRecommendations()

        self.max_depth = max_depth
        self.propagate_symptoms = symptoms
        self.propagate_risk = risk
        self.propagate_postive_test = True  # bare minimum
        self.should_modify_behavior = should_modify_behavior

        self.p_contact = 1
        self.delay = 0
        self.app = True
        if risk_model == "manual":
            assert not symptoms, "makes no sense to trace symptoms by phone...?"
            assert not risk, "don't make be believe we will trace risk by phone either"
            self.p_contact = conf.get("MANUAL_TRACING_P_CONTACT")
            self.delay = 1
            self.app = False

        self.propagate_risk_max_depth = max_depth
        # more than 3 will slow down the simulation too much
        if self.propagate_risk:
            self.propage_risk_max_depth = min(3, max_depth)

        if risk_model == "transformer":
            self.propagate_risk_max_depth = BIG_NUMBER
            self.propagate_risk = False
            self.propagate_symptoms = False

    def modify_behavior(self, human):
        if not self.should_modify_behavior and (not human.has_app and self.app):
            return
        return self.intervention.modify_behavior(human)

    def _get_hypothetical_contact_tracing_results(
            self,
            human: "Human",
            mailbox: "PersonalMailboxType",
            humans_map: typing.Dict[str, "Human"],
    ) -> typing.Tuple[int, int, typing.Tuple[int, int, int, int]]:
        """
        Returns the counts for the 'hypothetical' tracing methods that might be used in apps/real life.

        This function will use the target human's logged encounters to fetch all his contacts using the
        provided city-wide human map. The number of past days covered by the tracing will depend on the
        contact book's maximum history, which should be defined from `TRACING_N_DAYS_HISTORY`.

        Args:
            human: the human for which to generate the contact tracing counts.
            mailbox: centralized mailbox with all recent update messages for the target human.
            humans_map: a human-name-to-human-object reference map to pass to the contact book functions.

        Returns:
            t (int): Number of recent contacts that are tested positive.
            s (int): Number of recent contacts that have reported symptoms.
                r_up: Number of recent contacts that increased their risk levels.
                v_up: Average increase in magnitude of risk levels of recent contacts.
                r_down: Number of recent contacts that decreased their risk levels.
                v_down: Average decrease in magnitude of risk levels of recent contacts.
        """
        assert self.risk_model != "transformer", "we should never be in here!"
        assert self.risk_model in ["manual", "digital", "naive", "other"], "missing something?"
        t, s, r_up, r_down, v_up, v_down = 0, 0, 0, 0, 0, 0

        if self.risk_model == "manual":
            # test_tracing_delay = datetime.timedelta(days=1)  # 1 day was previously used by default
            raise NotImplementedError(  # TODO: complete implementation as detailed below
                "the current implementation does not log encounters if the users do not have the app; "
                "therefore, manual tracing is dead --- we could fix that by logging encounters all the "
                "time (with a global flab?) and by checking that flag in the tracing call below as well"
                # ... or by simply assuming everyone has an app?
            )
        else:
            test_tracing_delay = datetime.timedelta(days=0)
        positive_test_counts = human.contact_book.get_positive_contacts_counts(
            humans_map=humans_map,
            tracing_delay=test_tracing_delay,
            tracing_probability=self.p_contact,
            max_order=self.max_depth,
        )
        for order, count in positive_test_counts.items():
            t += count * np.exp(-2*(order-1))

        if self.propagate_symptoms:
            symptomatic_counts = human.contact_book.get_symptomatic_contacts_counts(
                humans_map=humans_map, max_order=self.max_depth)
            for order, count in symptomatic_counts.items():
                s += count * np.exp(-2*(order-1))

        if self.propagate_risk:
            # TODO: contact book is still missing the r_up,r_down,v_up,v_down tracing functions
            # note1: we could use the simpler `get_risk_level_update_counts` function instead?
            # note2: for whoever might want to reimplement the missing tracing, check the orig code
            # note3: the mailbox is passed into this function, we could give it to the contact book
            #        (or to a pure function from somewhere else) to fetch the 4 counts
            raise NotImplementedError
        return t, s, (r_up, v_up, r_down, v_down)

    def compute_risk(
            self,
            human: "Human",
            mailbox: "PersonalMailboxType",
            humans_map: typing.Dict[str, "Human"],
    ):
        """
        Computes the infection risk of a human based on the statistics of its past contacts.

        Args:
            human: the human for which to generate the contact tracing counts.
            mailbox: centralized mailbox with all recent update messages for the target human.
            humans_map: a human-name-to-human-object reference map to pass to the contact book functions.

        Returns:
            float: a scalar value.
        """
        assert self.risk_model != "transformer", "we should never be in here!"
        assert self.risk_model in ["manual", "digital", "naive", "other"], "missing something?"
        t, s, r = self._get_hypothetical_contact_tracing_results(human, mailbox, humans_map)
        if self.risk_model in ["manual", "digital"]:
            if t + s > 0:
                risk = 1.0
            else:
                risk = 0.0
        elif self.risk_model == "naive":
            risk = 1.0 - (1.0 - human.conf.get("RISK_TRANSMISSION_PROBA")) ** (t+s)
        elif self.risk_model == "other":
            r_up, v_up, r_down, v_down = r
            r_score = 2*v_up - v_down
            risk = 1.0 - (1.0 - human.conf.get("RISK_TRANSMISSION_PROBA")) ** (t + 0.5*s + r_score)
        return risk

    def compute_tracing_delay(self, human):
        """
        Computes delay for tracing. NOT IMPLEMENTED.

        Args:
            human (Human): `Human` object
        """
        pass # FIXME: circualr imports issue; can't import _draw_random_discreet_gaussian

    def __repr__(self):
        if self.risk_model == "transformer":
            return f"Tracing: {self.risk_model}"
        return f"Tracing: {self.risk_model} order {self.max_depth} symptoms: {self.propagate_symptoms} risk: {self.propagate_risk} modify:{self.should_modify_behavior}"


class CityInterventions(object):
    """
    Implements city based interventions such as opening or closing of stores/parks/miscs etc.
    """
    def __init__(self):
        pass

    def modify_city(self, city):
        """
        Modify attributes of city.

        Args:
            city (City): `City` object
        """
        pass

    def revert_city(self, city):
        """
        resets attributes of the city.

        Args:
            city (City): `City` object
        """
        pass


class TestCapacity(CityInterventions):
    """
    Change the test capacity of the city.
    """

    def modify_city(self, city):
        raise NotImplementedError

    def revert_city(self, city):
        raise NotImplementedError

def get_intervention(conf):
    """
    Returns the appropriate class of intervention.

    Args:
        conf (dict): configuration to send to intervention object.

    Raises:
        NotImplementedError: If intervention has not been implemented.

    Returns:
        `BehaviorInterventions`: `BehaviorInterventions` corresponding to the arguments.
    """
    key = conf.get("INTERVENTION")
    if key == "Lockdown":
        return Lockdown()
    elif key == "WearMask":
        return WearMask(conf.get("MASKS_SUPPLY"))
    elif key == "SocialDistancing":
        return SocialDistancing()
    elif key == "Quarantine":
        return Quarantine()
    elif key == "Tracing":
        return Tracing(conf)
    elif key == "WashHands":
        return WashHands()
    elif key == "StandApart":
        return StandApart()
    elif key == "StayHome":
        return StayHome()
    elif key == "GetTested":
        raise NotImplementedError
    else:
        raise
