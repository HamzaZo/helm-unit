#!/bin/sh

cd $HELM_PLUGIN_DIR
version="$(cat plugin.yaml | grep "version" | cut -d '"' -f 2)"
echo "Downloading and installing helm-unit v${version} ..."

# Find correct archive name
unameOut="$(uname -s)"
github_oauth_token=<TOKEN>
case "${unameOut}" in
    Linux*)     os=Linux;;
    Darwin*)    os=Darwin;;
    MINGW*)     os=windows;;
    *)          os="UNKNOWN:${unameOut}"
esac

arch=`uname -m`

# Get the "github tag id" of this release
github_tag_id=$(curl --silent --show-error \
                     --header "Authorization: token $github_oauth_token" \
                     --request GET \
                     "https://api.github.com/repos/HamzaZo/helm-unit/releases" \
                     | jq --raw-output ".[] | select(.tag_name==\"$version\").id")


# Get the download URL of our desired asset
download_url=$(curl --silent --show-error \
                    --header "Authorization: token $github_oauth_token" \
                    --header "Accept: application/vnd.github.v3.raw" \
                    --location \
                    --request GET \
                    "https://api.github.com/repos/HamzaZo/helm-unit/releases/$github_tag_id" \
                    | jq --raw-output ".assets[] | select(.name==\"helm-unit_${version}_${os}_${arch}.zip\").url")

# Get GitHub's S3 redirect URL
# Why not just curl's built-in "--location" option to auto-redirect? Because curl then wants to include all the original
# headers we added for the GitHub request, which makes AWS complain that we're trying strange things to authenticate.
redirect_url=$(curl --silent --show-error \
          --header "Authorization: token $github_oauth_token" \
          --header "Accept: application/octet-stream" \
          --request GET \
          --write-out "%{redirect_url}" \
          "$download_url")


# Finally download the actual binary
curl  --silent --show-error \
          --header "Accept: application/octet-stream" \
          --output "helm-unit_${version}_${os}_${arch}.zip" \
          --request GET \
          "$redirect_url"

# Install bin
rm -rf bin && mkdir bin && unzip helm-unit_${version}_${os}_${arch}.zip -d bin >/dev/null 2>&1 && rm -f helm-unit_${version}_${os}_${arch}.zip
 

echo "helm-unit ${version} is correctly installed."
echo
echo "See https://github.com/HamzaZo/helm-unit#getting-started for help getting started."
echo "Happy Helming testing day!."
