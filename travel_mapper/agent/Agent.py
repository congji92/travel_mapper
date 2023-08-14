from langchain.chains import LLMChain, SequentialChain
from langchain.chat_models import ChatOpenAI
from travel_mapper.agent.templates import (
    ValidationTemplate,
    ItineraryTemplate,
    MappingTemplate,
)
from travel_mapper.constants import MODEL_NAME, TEMPERATURE
import openai


class Agent(object):
    def __init__(self, open_ai_api_key, debug=True):
        openai.api_key = open_ai_api_key
        self.chat_model = ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)
        self.validation_prompt = ValidationTemplate()
        self.itinerary_prompt = ItineraryTemplate()
        self.mapping_prompt = MappingTemplate()

        self.validation_chain = self._set_up_validation_chain(debug)
        self.agent_chain = self._set_up_agent_chain(debug)

    def _set_up_validation_chain(self, debug=True):
        validation_agent = LLMChain(
            llm=self.chat_model,
            prompt=self.validation_prompt.chat_prompt,
            output_parser=self.validation_prompt.parser,
            output_key="validation_output",
            verbose=debug,
        )

        overall_chain = SequentialChain(
            chains=[validation_agent],
            input_variables=["query", "format_instructions"],
            output_variables=["validation_output"],
            verbose=debug,
        )

        return overall_chain

    def _set_up_agent_chain(self, debug=True):
        travel_agent = LLMChain(
            llm=self.chat_model,
            prompt=self.itinerary_prompt.chat_prompt,
            verbose=debug,
            output_key="agent_suggestion",
        )

        parser = LLMChain(
            llm=self.chat_model,
            prompt=self.mapping_prompt.chat_prompt,
            output_parser=self.mapping_prompt.parser,
            verbose=debug,
            output_key="mapping_list",
        )

        overall_chain = SequentialChain(
            chains=[travel_agent, parser],
            input_variables=["query", "format_instructions"],
            output_variables=["agent_suggestion", "mapping_list"],
            verbose=debug,
        )

        return overall_chain

    def suggest_travel(self, query):
        validation_result = self.validation_chain(
            {
                "query": query,
                "format_instructions": self.validation_prompt.parser.get_format_instructions(),
            }
        )

        validation_test = validation_result["validation_output"].dict()

        if validation_test["plan_is_valid"].lower() == "no":
            print("\n######\n Travel plan is not valid \n######\n")
            print(validation_test["updated_request"])
            return validation_result, _

        else:
            # plan is valid

            agent_result = self.agent_chain(
                {
                    "query": query,
                    "format_instructions": self.mapping_prompt.parser.get_format_instructions(),
                }
            )

            trip_suggestion = agent_result["agent_suggestion"]
            list_of_places = agent_result["mapping_list"].dict()

            return trip_suggestion, list_of_places