import iter8_analytics.api.analytics.request_parameters as request_parameters
import iter8_analytics.api.analytics.responses as responses
from collections import namedtuple
from datetime import datetime, timezone, timedelta
CHANGE_OBSERVED_STR = "change_observed"
SUCCESS_CRITERION_INFORMATION_STR="success_criterion_information"
EFFECTIVE_ITERATION_COUNT_STR="effective_iteration_count"

class CheckAndIncrementLastState():
    def __init__(self, baseline_traffic, candidate_traffic, baseline_success_criterion_information, candidate_success_criterion_information):
        self.last_state = {
            request_parameters.BASELINE_STR: {
                responses.TRAFFIC_PERCENTAGE_STR: baseline_traffic,
                SUCCESS_CRITERION_INFORMATION_STR: baseline_success_criterion_information
            },
            request_parameters.CANDIDATE_STR: {
                responses.TRAFFIC_PERCENTAGE_STR: candidate_traffic,
                SUCCESS_CRITERION_INFORMATION_STR: candidate_success_criterion_information
            },
            CHANGE_OBSERVED_STR: False
        }

class EpsilonTGreedyLastState():
    def __init__(self, baseline_traffic, candidate_traffic, baseline_success_criterion_information, candidate_success_criterion_information, effective_iteration_count):
        self.last_state = {
            request_parameters.BASELINE_STR: {
                responses.TRAFFIC_PERCENTAGE_STR: baseline_traffic,
                SUCCESS_CRITERION_INFORMATION_STR: baseline_success_criterion_information
            },
            request_parameters.CANDIDATE_STR: {
                responses.TRAFFIC_PERCENTAGE_STR: candidate_traffic,
                SUCCESS_CRITERION_INFORMATION_STR: candidate_success_criterion_information
            },
            CHANGE_OBSERVED_STR: False,
            EFFECTIVE_ITERATION_COUNT_STR: effective_iteration_count
        }

FIRST_ITERATION_STR = "first_iteration"
SUCCESS_CRITERION_BELIEF_STR = "success_criterion_belief"
REWARD_BELIEF_STR = "reward_belief"
class BayesianRoutingLastState():
    def __init__(self, baseline_criterion_beliefs, candidate_criterion_beliefs, baseline_reward_beliefs, candidate_reward_beliefs):
        self.last_state = {
            request_parameters.BASELINE_STR: {
             SUCCESS_CRITERION_BELIEF_STR: baseline_criterion_beliefs,
             REWARD_BELIEF_STR: baseline_reward_beliefs
             },
            request_parameters.CANDIDATE_STR: {
                SUCCESS_CRITERION_BELIEF_STR: candidate_criterion_beliefs,
                REWARD_BELIEF_STR: candidate_reward_beliefs
            }
        }


class ServicePayload():
    def __init__(self, service_payload):
        self.start_time = service_payload[request_parameters.START_TIME_PARAM_STR]
        self.end_time = str(datetime.now(timezone.utc)) if request_parameters.END_TIME_PARAM_STR not in service_payload else service_payload[request_parameters.END_TIME_PARAM_STR]
        self.tags = service_payload[request_parameters.TAGS_PARAM_STR]

class Criterion():
    def __init__(self, criterion):
        self.metric_name = criterion[request_parameters.METRIC_NAME_STR]
        self.is_counter = criterion[request_parameters.IS_COUNTER_STR]
        self.absent_value = "0.0" if request_parameters.ABSENT_VALUE_STR not in criterion else criterion[request_parameters.ABSENT_VALUE_STR]
        self.metric_query_template = criterion[request_parameters.METRIC_QUERY_TEMPLATE_STR]
        self.metric_sample_size_query_template = criterion[request_parameters.METRIC_SAMPLE_SIZE_QUERY_TEMPLATE]

    def generate_id(self, criterion):
        self.criterion_id = hash(frozenset(criterion.items()))
        return self.criterion_id


class FeasibilityCriterion(Criterion):
    def __init__(self, criterion):
        """
        criterion:  {
            "metric_name": "iter8_latency",
            "is_counter": False,
            "absent_value": "None",
            "metric_query_template": "sum(increase(istio_requests_total{response_code=~\"5..\",reporter=\"source\"}[$interval]$offset_str)) by ($entity_labels)",
            "metric_sample_size_query_template": "sum(increase(istio_requests_total{reporter=\"source\"}[$interval]$offset_str)) by ($entity_labels)",
            "type": "delta",
            "value": 0.02,
            "sample_size": 0,
            "stop_on_failure": false
            }
        """
        super().__init__(criterion)
        self.type = criterion[request_parameters.CRITERION_TYPE_STR]
        self.value = criterion[request_parameters.CRITERION_VALUE_STR]
        self.stop_on_failure = False if request_parameters.CRITERION_STOP_ON_FAILURE_STR not in criterion else criterion[request_parameters.CRITERION_STOP_ON_FAILURE_STR]


class FeasibilityCriterionDefault(FeasibilityCriterion):
    def __init__(self, criterion):
        """
        criterion:  {
            "metric_name": "iter8_latency",
            "is_counter": False,
            "absent_value": "None",
            "metric_query_template": "sum(increase(istio_requests_total{response_code=~\"5..\",reporter=\"source\"}[$interval]$offset_str)) by ($entity_labels)",
            "metric_sample_size_query_template": "sum(increase(istio_requests_total{reporter=\"source\"}[$interval]$offset_str)) by ($entity_labels)",
            "type": "delta",
            "value": 0.02,
            "sample_size": 10,
            "stop_on_failure": false
            }
        """
        super().__init__(criterion)
        self.sample_size = 10 if request_parameters.CRITERION_SAMPLE_SIZE_STR not in criterion else criterion[request_parameters.CRITERION_SAMPLE_SIZE_STR]
        self.min_max = None

class FeasibilityCriterionBR(FeasibilityCriterion):
    def __init__(self, criterion):
        """
        criterion:  {
            "metric_name": "iter8_latency",
            "is_counter": False,
            "absent_value": "None",
            "metric_query_template": "sum(increase(istio_requests_total{response_code=~\"5..\",reporter=\"source\"}[$interval]$offset_str)) by ($entity_labels)",
            "metric_sample_size_query_template": "sum(increase(istio_requests_total{reporter=\"source\"}[$interval]$offset_str)) by ($entity_labels)",
            "type": "delta",
            "value": 0.02,
            "min_max": {
                "min": 0,
                "max": 1
             },
            "sample_size": 0,
            "stop_on_failure": false
            }
        """
        super().__init__(criterion)
        self.sample_size = 0 #defaults to 0 for PBR/OBR
        self.min_max = None if request_parameters.MIN_MAX_STR not in criterion else criterion[request_parameters.MIN_MAX_STR]

class RewardCriterion(Criterion):
    def __init__(self, reward):
        super().__init__(reward)

class TrafficControlDefault():
    def __init__(self, traffic_control):
        self.success_criteria = []
        for each_criteria in traffic_control[request_parameters.SUCCESS_CRITERIA_STR]:
            self.success_criteria.append(FeasibilityCriterionDefault(each_criteria))
        self.step_size = 2 if request_parameters.STEP_SIZE_STR not in traffic_control else traffic_control[request_parameters.STEP_SIZE_STR]
        self.max_traffic_percent = 50 if request_parameters.MAX_TRAFFIC_PERCENT_STR not in traffic_control else traffic_control[request_parameters.MAX_TRAFFIC_PERCENT_STR]
        self.reward = None if request_parameters.REWARD_STR not in traffic_control else RewardCriterion(traffic_control[request_parameters.REWARD_STR])

class TrafficControlBR():
    def __init__(self, traffic_control):
        self.success_criteria = []
        for each_criteria in traffic_control[request_parameters.SUCCESS_CRITERIA_STR]:
            self.success_criteria.append(FeasibilityCriterionBR(each_criteria))
        self.confidence = 0.95 if request_parameters.CONFIDENCE_STR not in traffic_control else traffic_control[request_parameters.CONFIDENCE_STR]
        self.max_traffic_percent = 50 if request_parameters.MAX_TRAFFIC_PERCENT_STR not in traffic_control else traffic_control[request_parameters.MAX_TRAFFIC_PERCENT_STR]
        self.reward = None if request_parameters.REWARD_STR not in traffic_control else RewardCriterion(traffic_control[request_parameters.REWARD_STR])



class Experiment():
    def __init__(self, payload):
        self.experiment = {}
        baseline_payload = ServicePayload(payload[request_parameters.BASELINE_STR])
        candidate_payload = ServicePayload(payload[request_parameters.CANDIDATE_STR])
        self.experiment_type = "a/b" if request_parameters.REWARD_STR in payload[request_parameters.TRAFFIC_CONTROL_STR] else "canary"
        self.baseline = baseline_payload
        self.candidate = candidate_payload
        self.set_traffic_control_and_last_state(payload)

    def set_traffic_control_and_last_state(self):
        raise NotImplementedError()

class CheckAndIncrementExperiment(Experiment):
    def __init__(self, payload):
        super().__init__(payload)

    def set_traffic_control_and_last_state(self, payload):
        if not payload[request_parameters.LAST_STATE_STR]:  # if it is empty
            last_state = CheckAndIncrementLastState(100, 0, [], [])
            first_iteration = True
        else:
            last_state = CheckAndIncrementLastState(payload[request_parameters.LAST_STATE_STR][request_parameters.BASELINE_STR][responses.TRAFFIC_PERCENTAGE_STR], payload[request_parameters.LAST_STATE_STR][request_parameters.CANDIDATE_STR][responses.TRAFFIC_PERCENTAGE_STR], payload[request_parameters.LAST_STATE_STR][request_parameters.BASELINE_STR][SUCCESS_CRITERION_INFORMATION_STR], payload[request_parameters.LAST_STATE_STR][request_parameters.CANDIDATE_STR][SUCCESS_CRITERION_INFORMATION_STR])
            first_iteration = False
        traffic_control = TrafficControlDefault(payload[request_parameters.TRAFFIC_CONTROL_STR])
        self.last_state = last_state
        self.first_iteration = first_iteration
        self.traffic_control = traffic_control

class EpsilonTGreedyExperiment(Experiment):
    def __init__(self, payload):
        super().__init__(payload)

    def set_traffic_control_and_last_state(self, payload):
        if not payload[request_parameters.LAST_STATE_STR]:  # if it is empty
            last_state = EpsilonTGreedyLastState(100, 0, [], [], 0)
            first_iteration = True
        else:
            last_state = EpsilonTGreedyLastState(payload[request_parameters.LAST_STATE_STR][request_parameters.BASELINE_STR][responses.TRAFFIC_PERCENTAGE_STR], payload[request_parameters.LAST_STATE_STR][request_parameters.CANDIDATE_STR][responses.TRAFFIC_PERCENTAGE_STR], payload[request_parameters.LAST_STATE_STR][request_parameters.BASELINE_STR][SUCCESS_CRITERION_INFORMATION_STR], payload[request_parameters.LAST_STATE_STR][request_parameters.CANDIDATE_STR][SUCCESS_CRITERION_INFORMATION_STR], payload[request_parameters.LAST_STATE_STR][EFFECTIVE_ITERATION_COUNT_STR])
            first_iteration = False
        traffic_control = TrafficControlDefault(payload[request_parameters.TRAFFIC_CONTROL_STR])
        self.last_state = last_state
        self.first_iteration = first_iteration
        self.traffic_control = traffic_control

class BayesianRoutingExperiment(Experiment):
     def __init__(self, payload):
         super().__init__(payload)

     def set_traffic_control_and_last_state(self, payload):
         traffic_control = TrafficControlBR(payload[request_parameters.TRAFFIC_CONTROL_STR])
         params = namedtuple('params', 'alpha beta gamma sigma')
         if not payload[request_parameters.LAST_STATE_STR]:  # if it is empty
             last_state = BayesianRoutingLastState([], [], params(None, None, None, None), params(None, None, None, None))
             first_iteration = True
         else:
             last_state = BayesianRoutingLastState(payload[request_parameters.LAST_STATE_STR][request_parameters.BASELINE_STR][SUCCESS_CRITERION_BELIEF_STR], payload[request_parameters.LAST_STATE_STR][request_parameters.CANDIDATE_STR][SUCCESS_CRITERION_BELIEF_STR], params(None, None, None, None), params(None, None, None, None))
             first_iteration = False
         self.traffic_control = traffic_control
         self.last_state = last_state
         self.first_iteration = first_iteration
