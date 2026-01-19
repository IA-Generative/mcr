from pydantic_settings import SettingsConfigDict, BaseSettings
from keycloak import KeycloakAdmin, KeycloakPutError
import csv


class Settings(BaseSettings):
    """
    To target other envs, you can fill the env files with vars prefixed YOUR_ENV_, and change the `env_prefix` below
    """

    KEYCLOAK_URL: str
    KEYCLOAK_ADMIN_REALM: str
    KEYCLOAK_APP_REALM: str
    KEYCLOAK_CLIENT_ID: str
    USERNAME: str
    PASSWORD: str
    GROUP_NAME: str
    FILE_PATH: str

    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file="./provisioning.env", env_prefix="PRD_", extra="allow"
    )


settings = Settings()
stats = {
    "success": {
        "create": 0,
        "get": 0,
    },
    "errors": {"400": 0, "409": 0},
}
keycloak_admin = KeycloakAdmin(
    server_url=settings.KEYCLOAK_URL,
    username=settings.USERNAME,
    password=settings.PASSWORD,
    realm_name=settings.KEYCLOAK_APP_REALM,
    user_realm_name=settings.KEYCLOAK_ADMIN_REALM,
    verify=True,
)


def get_user(user_dict: dict) -> str | None:
    try:
        user_id = keycloak_admin.get_user_id(user_dict["email"])

        if settings.DEBUG and user_id is not None:
            print(f"Got user: {user_id}")

        return user_id
    except Exception as e:
        print(f"Error getting user: {e}")
        raise e


def delete_user(user_dict: dict) -> None:
    try:
        user_id = keycloak_admin.get_user_id(user_dict["email"])
        keycloak_admin.delete_user(user_id)

        if settings.DEBUG and user_id is not None:
            print(f"Got user: {user_id}")

    except Exception as e:
        print(f"Error deleting user: {e}")
        raise e


def create_user(user_dict: dict) -> str | None:
    try:
        user_id = keycloak_admin.create_user(
            {
                "email": user_dict["email"],
                "username": user_dict["email"],
                "enabled": True,
                "firstName": user_dict.get("firstName", ""),
                "lastName": "",
                "emailVerified": True,
                "credentials": [],
            }
        )
        if settings.DEBUG and user_id is not None:
            print(f"Created user: {user_id}")

        return user_id
    except Exception as e:
        print(f"User creation: {e}")
        raise e


def get_or_create_group(group_name: str) -> str:
    try:
        groups = keycloak_admin.get_groups()
        group = next((g for g in groups if g["name"] == group_name), None)

        if not group:
            group_id = keycloak_admin.create_group({"name": group_name})

            if settings.DEBUG:
                print(f"Created group '{group_name}'.")
            return group_id

        return group["id"]

    except Exception as e:
        print(f"Error getting group: {e}")
        raise e


def add_user_to_group(user_id: int, group_id: str) -> None:
    try:
        keycloak_admin.group_user_add(user_id, group_id)
        if settings.DEBUG:
            print(f"User '{user_id}' added to group.")

    except KeycloakPutError as e:
        print(f"Error adding user to group: {e}")
        raise e


def make_beta_tester(user_data: dict, group_id: str) -> bool:
    try:
        user_id = get_user(user_data)
        if user_id:
            stats["success"]["get"] += 1
        else:
            user_id = create_user(user_data)
            stats["success"]["create"] += 1

        add_user_to_group(user_id, group_id)
        return True
    except Exception as e:
        print(f"Failed treating: {user_data}")
        if e.response_code == 400 or e.response_code == 409:
            stats["errors"][str(e.response_code)] += 1
        return False


def parse_csv_to_dicts(file_path: str) -> list[dict]:
    with open(file_path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [row for row in reader]


def make_from_file() -> None:
    rows = parse_csv_to_dicts(settings.FILE_PATH)
    failed = []

    group_id = get_or_create_group(settings.GROUP_NAME)
    count = 0
    for user_data in rows:
        result = make_beta_tester(user_data, group_id)
        # delete_user(user_data)
        if result:
            count += 1
        else:
            failed.append(user_data["email"])

        if count % 10 == 0:
            print(count)

    print(f"Success rate: {count} / {len(rows)}")


def delete_from_group() -> None:
    group_id = get_or_create_group(settings.GROUP_NAME)
    users = keycloak_admin.get_group_members(group_id)

    count = 0
    for user_data in users:
        delete_user(user_data)
        count += 1

        if count % 10 == 0:
            print(count)

    print(f"Success rate: {count} / {len(users)}")


# Activate the necessary function
make_from_file()
# delete_from_group()

print(stats)
