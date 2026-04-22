FROM node:20-alpine

WORKDIR /workspace

COPY package.json /workspace/package.json
COPY tsconfig.base.json /workspace/tsconfig.base.json
COPY apps/web/package.json /workspace/apps/web/package.json
COPY packages/shared-types/package.json /workspace/packages/shared-types/package.json
COPY packages/ui/package.json /workspace/packages/ui/package.json

RUN npm install

COPY . /workspace

WORKDIR /workspace/apps/web

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]

