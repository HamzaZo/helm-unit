#!/bin/sh

## Inspired by https://github.com/nouney/helm-gcs/blob/master/scripts/install.sh

cd $HELM_PLUGIN_DIR
version="$(cat plugin.yaml | grep "version" | cut -d '"' -f 2)"
echo "Downloading and installing helm-unit v${version} ..."

# Find correct archive name
unameOut="$(uname -s)"

case "${unameOut}" in
    Linux*)     os=Linux;;
    Darwin*)    os=Darwin;;
    MINGW*)     os=windows;;
    *)          os="UNKNOWN:${unameOut}"
esac

arch=`uname -m`
url="https://github.com/HamzaZo/helm-unit/releases/download/v${version}/helm-unit_${version}_${os}_${arch}.tar.gz"


if [ "$url" = "" ]
then
    echo "Unsupported OS / architecture: ${os}_${arch}"
    exit 1
fi

filename=`echo ${url} | sed -e "s/^.*\///g"`

# Download archive
if [ -n $(command -v curl) ]
then
    curl -sSL -O $url
elif [ -n $(command -v wget) ]
then
    wget -q $url
else
    echo "Need curl or wget"
    exit -1
fi

# Install bin
rm -rf bin && mkdir bin && tar xzvf $filename -C bin > /dev/null && rm -f $filename

echo "helm-unit ${version} is correctly installed."
echo
echo "See https://github.com/HamzaZo/helm-unit#getting-started for help getting started."
echo "Happy Helming testing day!."