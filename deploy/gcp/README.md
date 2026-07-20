# Despliegue GCP: asignar-folder

Destino: `myma-496119`, VM `labmyma-apps`, zona `us-east1-c`.

## Secretos requeridos

- `acreditacion-asignar-folder-supabase-key`
- `acreditacion-asignar-folder-google-client-secret`
- `acreditacion-asignar-folder-google-token`
- `acreditacion-asignar-folder-api-token`

`materialize-secrets.sh` los obtiene con la service account de la VM y los
escribe temporalmente bajo `/run/myma/asignar-folder`. Nunca deben copiarse a
Git ni imprimirse en logs.

## Orden de instalacion

1. Preservar la imagen activa con el tag `49a3424-precutover`.
2. Instalar `myma-asignar-folder.service` y definir `APP_VERSION` en
   `/etc/default/myma-asignar-folder`.
3. Instalar Certbot 5.4+ en `/opt/certbot-ip`.
4. Instalar el snippet ACME dentro del servidor HTTP existente y recargar Nginx.
5. Ejecutar `issue-ip-certificate.sh`; solo despues instalar el servidor HTTPS.
6. Instalar y habilitar `certbot-ip-renew.timer`.

## Rollback

Cambiar `APP_VERSION` a `49a3424-precutover`, ejecutar
`systemctl restart myma-asignar-folder` y verificar el health local. Si el
problema corresponde al proxy, revertir el ultimo deploy de Render sin cambiar
`ACREDITACION_LEGACY_API_BASE_URL`.
