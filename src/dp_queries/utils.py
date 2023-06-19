import io
from fastapi.responses import StreamingResponse


def stream_dataframe(df):
    stream = io.StringIO()

    # CSV creation
    df.to_csv(stream, index=False)

    response = StreamingResponse(
        iter([stream.getvalue()]), media_type="text/csv"
    )
    print("here")
    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=synthetic_data.csv"
    print("and here")
    return response
