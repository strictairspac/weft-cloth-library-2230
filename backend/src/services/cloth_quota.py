"""Build warehouse decisions from reconciled stock and current active batches."""

from collections import defaultdict


def warehouse_plan(reconciled, active_batches, quotas):
    stock_by_grade = {row['grade']: row for row in reconciled}
    quota_by_grade = {row['grade']: row for row in quotas}
    batches_by_grade = defaultdict(list)
    for batch in active_batches:
        batches_by_grade[batch['grade']].append(batch)

    decisions = []
    cuts = []
    for grade in sorted(stock_by_grade.keys() | quota_by_grade.keys()):
        stock = stock_by_grade.get(grade)
        weight = stock['incremental_weight'] if stock else 0
        pieces = stock['incremental_pieces'] if stock else 0
        quota = quota_by_grade.get(grade)
        decision = {'等级': grade, '当前重量（克）': weight, '当前件数': pieces}
        if quota is None:
            decisions.append({**decision, '判定': '缺少配额，暂停该等级发单'})
            continue

        weight_limit = quota['capacity_g']
        piece_limit = quota['capacity_pieces']
        excess_weight = max(0, weight - weight_limit)
        excess_pieces = max(0, pieces - piece_limit)
        remaining_weight, remaining_pieces = weight, pieces
        for batch in batches_by_grade[grade]:
            if remaining_weight <= weight_limit and remaining_pieces <= piece_limit:
                break
            remaining_weight -= batch['weight_g']
            remaining_pieces -= batch['pieces']
            cuts.append({
                '等级': grade, '批次': batch['batch_id'], '修订号': batch['revision'],
                '转裁重量（克）': batch['weight_g'], '转裁件数': batch['pieces'],
                '转出后在库重量（克）': remaining_weight, '转出后在库件数': remaining_pieces,
            })
        decisions.append({
            **decision,
            '重量配额（克）': weight_limit, '件数配额': piece_limit,
            '超重（克）': excess_weight, '超件数': excess_pieces,
            '建议执行后可用重量（克）': weight_limit - remaining_weight,
            '建议执行后可用件数': piece_limit - remaining_pieces,
            '判定': '建议整批转入裁切区' if excess_weight or excess_pieces else '仓位符合配额',
        })
    return decisions, cuts, len(stock_by_grade.keys() - quota_by_grade.keys())
