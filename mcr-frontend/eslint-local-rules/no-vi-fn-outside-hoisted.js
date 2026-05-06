/** @type {import('eslint').Rule.RuleModule} */

function isViFn(node) {
  return (
    node.callee.type === 'MemberExpression' &&
    node.callee.object.name === 'vi' &&
    node.callee.property.name === 'fn'
  );
}

function isNodeInFunction(ancestor) {
  return (
    ancestor.type === 'FunctionExpression' ||
    ancestor.type === 'FunctionDeclaration' ||
    ancestor.type === 'ArrowFunctionExpression'
  )
}

function isNodeInViHoisted(ancestor) {
  return (
    ancestor.type === 'CallExpression' &&
    ancestor.callee.type === 'MemberExpression' &&
    ancestor.callee.object.name === 'vi' &&
    ancestor.callee.property.name === 'hoisted'
  );
}

module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description:
        'Interdit vi.fn() au niveau module sans vi.hoisted() — risque TDZ avec vi.mock()',
    },
    messages: {
      noViFnOutsideHoisted:
        'vi.fn() déclaré au niveau module : risque de TDZ avec vi.mock(). Utiliser vi.hoisted(() => ({ mockX: vi.fn() })) à la place.',
    },
    schema: [],
  },
  create(context) {
    return {
      CallExpression(node) {
        if (!isViFn(node)) {
          return;
        }

        let ancestor = node.parent;
        while (ancestor) {
          if (isNodeInFunction(ancestor)) {
            return;
          }
          if (isNodeInViHoisted(ancestor)) {
            // Dans vi.hoisted() — OK
            return;
          }
          ancestor = ancestor.parent;
        }

        context.report({ node, messageId: 'noViFnOutsideHoisted' });
      },
    };
  },
};
