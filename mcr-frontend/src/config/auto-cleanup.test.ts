import { render, screen } from '@testing-library/vue';

describe('Auto DOM cleanup test', () => {
  it('should render an element to be cleaned up', () => {
    // Render a simple element
    render({ template: '<div data-testid="cleanup-test">Hello</div>' });
    expect(screen.getByTestId('cleanup-test')).toBeInTheDocument();
  });

  it('should not find the element from the previous test', () => {
    // The element from the previous test should be gone
    expect(screen.queryByTestId('cleanup-test')).toBeNull();
  });
});
