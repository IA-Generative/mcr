vault {
  address = "" # uses VAULT_ADDR env var
}

auto_auth {
  method "token_file" {
    config = {
      token_file_path = "__VAULT_TOKEN_PATH__"
    }
  }
}

template {
  source      = "__PROJECT_ROOT__/tpl/env.ctmpl"
  destination = "__PROJECT_ROOT__/.env"
  perms       = 0600
  error_on_missing_key = true
}
