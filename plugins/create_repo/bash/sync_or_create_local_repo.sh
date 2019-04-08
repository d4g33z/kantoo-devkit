#!/usr/bin/env sh

if [ -d "/entropy/artifacts/standard" ]; then
  echo "=== Repository already exists, syncronizing ==="
  eit unlock ${REPOSITORY_NAME} || true
  eit pull --quick ${REPOSITORY_NAME} || true
  #eit sync ${{repo}}
else
  echo "=== Repository is empty, intializing ==="
  echo "Yes" | eit init --quick ${REPOSITORY_NAME}
#  eit push --quick --force
fi

