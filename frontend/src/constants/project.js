export const topic = {
  "name": "纬回布库·捐布分级汇总",
  "direction": "物化汇总与增量修正",
  "modules": [
    "捐赠称重",
    "批次修正",
    "增量汇总",
    "仓位配额单"
  ],
  "algorithm": "撤销旧贡献再累加新贡献，和 SQL 全量汇总核对仓位重量与件数"
};
