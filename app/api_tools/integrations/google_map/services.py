from django.conf import settings
from googlemaps import Client
from ulid import ULID

from app.common.utils.signed_url import SignedURL


class GoogleMapServices:
    MAP_BASE_URL = f"{settings.HOST.rstrip('/')}/api/tools/google-map/map/"

    client = Client(key=settings.GOOGLE_MAPS_API_KEY)

    @classmethod
    def get_location(
        cls, location: str, keyword: str, type: str, radius=5000, next_page_token=None
    ) -> dict:
        # Geocode the location string to obtain lat/lng coordinates
        geocode_results = cls.client.geocode(location)
        if not geocode_results:
            return {"error": f"Could not geocode location: {location}", "results": []}

        latlng = geocode_results[0]["geometry"]["location"]
        coords = (latlng["lat"], latlng["lng"])

        # Search for nearby places using the resolved coordinates
        nearby_results = cls.client.places_nearby(
            location=coords,
            keyword=keyword,
            type=type,
            radius=radius,
            page_token=next_page_token,
        )

        return nearby_results

    @staticmethod
    def _build_signed_map_url(query: str) -> str:
        """Build a signed map URL embedding the query in a tamper-proof token."""
        token = SignedURL.generate_token(settings.SECRET_KEY, q=query, key=str(ULID()))
        return f"{GoogleMapServices.MAP_BASE_URL}?token={token}"

    @staticmethod
    def _build_photo_url(photo_reference: str, max_width: int = 200) -> str:
        """Build a Google Maps Places Photo API URL from a photo_reference."""
        return (
            f"https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth={max_width}"
            f"&photo_reference={photo_reference}"
            f"&key={settings.GOOGLE_MAPS_API_KEY}"
        )

    @staticmethod
    def simple_output(result: dict) -> dict:
        """Simplify the raw places_nearby response into an easy-to-read format."""
        places = []
        markdown_lines: list[str] = []

        for idx, place in enumerate(result.get("results", []), start=1):
            opening_hours = place.get("opening_hours", {})
            # Extract image URL from the first photo reference, if available
            photos = place.get("photos", [])
            image_url: str | None = None
            if photos:
                photo_ref = photos[0].get("photo_reference")
                if photo_ref:
                    image_url = GoogleMapServices._build_photo_url(photo_ref)

            name = place.get("name")
            address = place.get("vicinity")
            rating = place.get("rating")
            total_ratings = place.get("user_ratings_total")
            open_now = opening_hours.get("open_now")
            business_status = place.get("business_status")
            place_id = place.get("place_id")

            map_url: str | None = (
                GoogleMapServices._build_signed_map_url(f"place_id:{place_id}")
                if place_id
                else None
            )

            places.append(
                {
                    "name": name,
                    "address": address,
                    "rating": rating,
                    "total_ratings": total_ratings,
                    "open_now": open_now,
                    "business_status": business_status,
                    "image_link": image_url,
                    "map_link": map_url,
                }
            )

            # Build markdown section for this place
            markdown_lines.append(f"### {idx}. {name or 'Unknown Place'}")
            if image_url:
                markdown_lines.append(f"![{name or 'Photo'}]({image_url})")
            if address:
                place_map_url = f"({map_url})" if place_id else ""
                markdown_lines.append(f"**Address:** [{address}]{place_map_url}")
            if rating is not None:
                ratings_str = f" ({total_ratings} reviews)" if total_ratings else ""
                markdown_lines.append(f"**Rating:** {rating}/5{ratings_str}")
            if open_now is not None:
                markdown_lines.append(f"**Open now:** {'Yes' if open_now else 'No'}")
            if business_status:
                markdown_lines.append(f"**Status:** {business_status}")
            if map_url:
                markdown_lines.append(f"[📍 View on map]({map_url})")
            markdown_lines.append("")  # blank line between entries

        markdown_content = "\n".join(markdown_lines)

        return {
            "data": places,
            "content": markdown_content,
            "next_page_token": result.get("next_page_token"),
        }
