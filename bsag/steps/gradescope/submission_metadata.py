from pathlib import Path

from devtools import debug
from pydantic import FilePath

from bsag import BaseStepConfig, BaseStepDefinition
from bsag.bsagio import BSAGIO

from ._types import METADATA_KEY, RESULTS_KEY, Results, SubmissionMetadata


class SubMetadataConfig(BaseStepConfig):
    submission_metatada_path: FilePath = Path("/autograder/submission_metadata.json")


class ReadSubMetadata(BaseStepDefinition[SubMetadataConfig]):
    @staticmethod
    def name() -> str:
        return "gradescope.sub_info"

    @classmethod
    def display_name(cls, _config: SubMetadataConfig) -> str:
        return "Submission Metadata"

    @classmethod
    def run(cls, bsagio: BSAGIO, config: SubMetadataConfig) -> bool:
        data = bsagio.data
        sub_metadata = SubmissionMetadata.parse_file(config.submission_metatada_path)
        data[METADATA_KEY] = sub_metadata
        data[RESULTS_KEY] = Results()

        bsagio.private.trace(
            "Submission metadata:\n" + debug.format(sub_metadata).str(highlight=bsagio.colorize_private)
        )

        return True
