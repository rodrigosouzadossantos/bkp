class FeatureExtractor:
  """
  Base class for all feature extractors.
  """

  name = "base"
  order = 100
  enabled = True

  def extract(self, ctx: dict) -> dict:
    raise NotImplementedError

  def schema(self) -> dict:
    """
    Return Spark schema mapping:
    {
        "col_name": DataType
    }
    """
    return {}
