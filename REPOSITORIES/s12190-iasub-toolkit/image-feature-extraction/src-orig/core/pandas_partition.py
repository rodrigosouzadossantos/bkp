import pandas as pd
import numpy as np
import cv2
from pyspark.sql.types import StructType


def pandas_partition(features):

    def _inner(iterator):

        import pandas as pd
        import numpy as np
        import cv2

        for pdf in iterator:

            # -----------------------------
            # BATCH DECODE (FAST)
            # -----------------------------
            contents = pdf["content"].values

            imgs = []
            grays = []

            for content in contents:
                nparr = np.frombuffer(content, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                imgs.append(img)
                grays.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))

            pdf["img"] = imgs
            pdf["gray"] = grays

            results = []

            # -----------------------------
            # FAST LOOP (no iterrows)
            # -----------------------------
            for i in range(len(pdf)):
                row = pdf.iloc[i]

                ctx = {
                    "path": row["path"],
                    "img": row["img"],
                    "gray": row["gray"],
                    "content": row["content"]
                }

                result = {"path": ctx["path"]}

                for f in features:
                    try:
                        result.update(f["extract"](ctx))
                    except:
                        pass

                results.append(result)

            yield pd.DataFrame(results)

    return _inner
