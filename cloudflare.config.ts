import { bindings, defineConfig, defineContainer, defineWorker, exports } from "@cloudflare/config";

const apiImage = defineContainer({
  name: "retriever-api",
  image: { dockerfile: "./Dockerfile" },
});

export default defineConfig({
  containers: [apiImage],
  worker: defineWorker({
    name: "retriever-api",
    entrypoint: "./workers/retriever-api/src/index.ts",
    compatibilityDate: "2026-11-24",
    exports: {
      RetrieverApi: exports.durableObject({
        storage: "sqlite",
        container: apiImage,
      }),
    },
    env: {
      RETRIEVER_API: bindings.durableObject({
        worker: "retriever-api",
        exportName: "RetrieverApi",
      }),
      DATABASE_URL: bindings.secret(),
      WEB_ORIGIN: bindings.text("*"),
      DRY_RUN: bindings.text("true"),
    },
  }),
});
